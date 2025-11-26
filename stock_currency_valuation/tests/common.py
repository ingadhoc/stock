import unittest

from freezegun import freeze_time
from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestStockCurrencyValuationCommon(TransactionCase):
    """Fixture base para los tests del walkthrough numérico definido en TESTING.md.

    Mapeo con la doc:
      - "ARS" (moneda de la compañía) → `cls.company_currency`
      - "USD" (moneda secundaria de la categoría) → `cls.secondary_currency`

    Las tasas se mantienen con los mismos valores que TESTING.md:
      Día 1: 1/1000  (≈ 0.001000)
      Día 2: 1/1200  (≈ 0.000833)
      Día 3: 1/1500  (≈ 0.000667)
    """

    DAY_1 = "2024-01-01"
    DAY_2 = "2024-01-02"
    DAY_3 = "2024-01-03"
    RATE_D1 = 1 / 1000.0
    RATE_D2 = 1 / 1200.0
    RATE_D3 = 1 / 1500.0
    INVERSE_D1 = 1000.0
    INVERSE_D2 = 1200.0
    INVERSE_D3 = 1500.0

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        if "purchase.order" not in cls.env:
            raise unittest.SkipTest(
                "stock_currency_valuation tests requieren purchase_stock instalado para las recepciones de compra."
            )

        cls.company = cls.env.company

        if not cls.company.chart_template:
            cls.env["account.chart.template"]._load("generic_coa", cls.company, install_demo=False)

        cls.company_currency = cls.company.currency_id

        cls.secondary_currency = cls.env["res.currency"].create(
            {
                "name": "SCV",  # nombre único para evitar colisión con currencies pre-existentes
                "symbol": "$",
                "rounding": 0.01,
            }
        )

        for date_str, rate in (
            (cls.DAY_1, cls.RATE_D1),
            (cls.DAY_2, cls.RATE_D2),
            (cls.DAY_3, cls.RATE_D3),
        ):
            cls.env["res.currency.rate"].create(
                {
                    "name": date_str,
                    "rate": rate,
                    "currency_id": cls.secondary_currency.id,
                    "company_id": cls.company.id,
                }
            )

        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.company.id)], limit=1)
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.supplier_location = cls.env.ref("stock.stock_location_suppliers")
        cls.customer_location = cls.env.ref("stock.stock_location_customers")
        cls.picking_type_in = cls.warehouse.in_type_id
        cls.picking_type_out = cls.warehouse.out_type_id

        cls.vendor = cls.env["res.partner"].create({"name": "SCV Vendor"})
        cls.customer = cls.env["res.partner"].create({"name": "SCV Customer"})

        cls.category = cls.env["product.category"].create(
            {
                "name": "Avco real_time SCV",
                "property_cost_method": "average",
                "property_valuation": "real_time",
            }
        )
        cls.category.with_company(cls.company).valuation_currency_id = cls.secondary_currency

        cls.uom_unit = cls.env.ref("uom.product_uom_unit")
        cls.product = cls.env["product.product"].create(
            {
                "name": "Producto P",
                "is_storable": True,
                "standard_price": 0.0,
                "categ_id": cls.category.id,
                "uom_id": cls.uom_unit.id,
            }
        )

        cls.lc_service = cls.env["product.product"].create(
            {
                "name": "Landed Cost SCV",
                "type": "service",
                "categ_id": cls.env.ref("product.product_category_goods").id,
            }
        )
        cls.lc_journal = cls.env["account.journal"].search(
            [("type", "=", "purchase"), ("company_id", "=", cls.company.id)],
            limit=1,
        )

    # ------------------------------------------------------------------
    # Helpers de operaciones
    # ------------------------------------------------------------------

    def _purchase_receipt(self, qty, price_unit, inverse_rate, date_str):
        """Crea PO + valida la recepción seteando manualmente la cotización."""
        with freeze_time(date_str):
            po = self.env["purchase.order"].create(
                {
                    "partner_id": self.vendor.id,
                    "order_line": [
                        Command.create(
                            {
                                "product_id": self.product.id,
                                "product_qty": qty,
                                "price_unit": price_unit,
                                "name": self.product.name,
                                "product_uom_id": self.uom_unit.id,
                                "date_planned": date_str,
                            }
                        )
                    ],
                }
            )
            po.button_confirm()
            picking = po.picking_ids[:1]
            self.assertEqual(len(picking), 1, "Se esperaba una recepción tras confirmar la PO.")
            picking.inverse_currency_rate = inverse_rate
            move = picking.move_ids
            move.quantity = qty
            move.picked = True
            picking.button_validate()
            self.assertEqual(picking.state, "done")
            return picking, move

    def _delivery(self, qty, date_str):
        with freeze_time(date_str):
            picking = self.env["stock.picking"].create(
                {
                    "partner_id": self.customer.id,
                    "picking_type_id": self.picking_type_out.id,
                    "location_id": self.stock_location.id,
                    "location_dest_id": self.customer_location.id,
                    "move_ids": [
                        Command.create(
                            {
                                "product_id": self.product.id,
                                "product_uom_qty": qty,
                                "product_uom": self.uom_unit.id,
                                "location_id": self.stock_location.id,
                                "location_dest_id": self.customer_location.id,
                            }
                        )
                    ],
                }
            )
            picking.action_confirm()
            picking.action_assign()
            move = picking.move_ids
            move.quantity = qty
            move.picked = True
            picking.button_validate()
            self.assertEqual(picking.state, "done")
            return picking, move

    def _return(self, source_picking, qty, date_str):
        with freeze_time(date_str):
            wiz = (
                self.env["stock.return.picking"]
                .with_context(
                    active_id=source_picking.id,
                    active_ids=source_picking.ids,
                    active_model="stock.picking",
                )
                .create({})
            )
            for line in wiz.product_return_moves:
                line.quantity = qty
            action = wiz.action_create_returns()
            return_pick = self.env["stock.picking"].browse(action["res_id"])
            move = return_pick.move_ids
            move.quantity = qty
            move.picked = True
            return_pick.button_validate()
            self.assertEqual(return_pick.state, "done")
            return return_pick, move

    def _inventory_adjustment(self, new_qty, date_str):
        """Setea el inventario absoluto a new_qty vía stock.quant. Devuelve el move generado."""
        with freeze_time(date_str):
            existing = self.env["stock.quant"].search(
                [
                    ("product_id", "=", self.product.id),
                    ("location_id", "=", self.stock_location.id),
                    ("company_id", "=", self.company.id),
                ],
                limit=1,
            )
            if existing:
                quant = existing.with_context(inventory_mode=True)
                quant.inventory_quantity = new_qty
            else:
                quant = (
                    self.env["stock.quant"]
                    .with_context(inventory_mode=True)
                    .create(
                        {
                            "product_id": self.product.id,
                            "location_id": self.stock_location.id,
                            "inventory_quantity": new_qty,
                        }
                    )
                )
            quant.action_apply_inventory()
            moves = self.env["stock.move"].search(
                [
                    ("product_id", "=", self.product.id),
                    ("date", ">=", date_str),
                    ("state", "=", "done"),
                ],
                order="id desc",
                limit=1,
            )
            return quant, moves

    def _landed_cost(self, picking, amount, inverse_rate, date_str):
        with freeze_time(date_str):
            lc = self.env["stock.landed.cost"].create(
                {
                    "picking_ids": [Command.set(picking.ids)],
                    "account_journal_id": self.lc_journal.id,
                    "cost_lines": [
                        Command.create(
                            {
                                "product_id": self.lc_service.id,
                                "name": "LC line",
                                "price_unit": amount,
                                "split_method": "by_quantity",
                            }
                        )
                    ],
                }
            )
            lc.inverse_currency_rate = inverse_rate
            lc.compute_landed_cost()
            lc.button_validate()
            self.assertEqual(lc.state, "done")
            return lc

    # ------------------------------------------------------------------
    # Helpers de aserción
    # ------------------------------------------------------------------

    def _product(self):
        """Producto en contexto de la compañía (necesario para campos company_dependent)."""
        return self.product.with_company(self.company)

    def _assert_almost(self, actual, expected, places=2, msg=""):
        self.assertAlmostEqual(actual, expected, places=places, msg=msg)
