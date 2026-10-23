from odoo import fields
from odoo.tests.common import TransactionCase, tagged

from .common import bill_with_price_difference, has_purchase_journal, receive_purchase, set_on_hand


@tagged("post_install", "-at_install")
class TestCurrencyCostPaths(TransactionCase):
    """El costo en moneda tiene que acompañar al de la compañía."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.company.id)], limit=1)
        cls.categ = cls.env["product.category"].create(
            {
                "name": "Categoria valuada en moneda",
                "property_cost_method": "average",
                "property_valuation": "manual_periodic",
                "valuation_currency_id": cls.env.ref("base.USD").id,
            }
        )
        cls.product = (
            cls.env["product.product"]
            .create({"name": "Producto valuado en moneda", "is_storable": True, "categ_id": cls.categ.id})
            .with_company(cls.company)
        )
        cls.product.standard_price = 1000.0
        cls.product.standard_price_in_currency = 100.0

    def _new_product(self, name, categ=None):
        return (
            self.env["product.product"]
            .create({"name": name, "is_storable": True, "categ_id": (categ or self.categ).id})
            .with_company(self.company)
        )

    def _layers(self):
        return self.env["stock.valuation.layer"].search(
            [("product_id", "=", self.product.id), ("company_id", "=", self.company.id)]
        )

    def test_inventory_adjustment_with_stock_keeps_currency_cost(self):
        """Un ajuste que suma stock entra al costo actual, no a 0 (antes partia el costo a la mitad)."""
        set_on_hand(self.env, self.product, 1.0)
        set_on_hand(self.env, self.product, 2.0)

        self.assertAlmostEqual(self.product.standard_price, 1000.0, places=2)
        self.assertAlmostEqual(self.product.standard_price_in_currency, 100.0, places=2)
        self.assertAlmostEqual(sum(self._layers().mapped("value_in_currency")), 200.0, places=2)

    def test_landed_cost_layer_reads_cost_method_of_its_company(self):
        """El costo en destino suma al costo en moneda aunque quien lo valida tenga otra compañia activa."""
        set_on_hand(self.env, self.product, 2.0)
        other_company = self.env["res.company"].create({"name": "Otra compañia"})
        self.env.user.company_ids |= other_company
        # en la otra compañia la categoria no es costo promedio
        self.categ.with_company(other_company).property_cost_method = "standard"

        journal = self.env["account.journal"].search([("company_id", "=", self.company.id)], limit=1)
        if not journal:
            self.skipTest("La compañia no tiene diarios contables")
        landed_cost = self.env["stock.landed.cost"].create(
            {"company_id": self.company.id, "account_journal_id": journal.id}
        )
        layer = (
            self.env["stock.valuation.layer"]
            .with_context(allowed_company_ids=[other_company.id, self.company.id])
            .create(
                {
                    "product_id": self.product.id,
                    "company_id": self.company.id,
                    "quantity": 0,
                    "value": 200.0,
                    "unit_cost": 0,
                    "remaining_qty": 0,
                    "stock_landed_cost_id": landed_cost.id,
                    "stock_valuation_layer_id": self._layers()[:1].id,
                    "description": "Costo en destino",
                }
            )
        )

        self.assertTrue(layer.value_in_currency)
        self.assertAlmostEqual(self.product.standard_price_in_currency, 100.0 + layer.value_in_currency / 2.0, places=2)

    def test_unpriced_receipt_values_layer_at_currency_cost(self):
        """Una recepcion sin compra y sin precio entra al costo actual, como un ajuste de inventario."""
        set_on_hand(self.env, self.product, 2.0)
        # reception from the supplier without purchase order nor price
        supplier_location = self.env.ref("stock.stock_location_suppliers")
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.warehouse.in_type_id.id,
                "location_id": supplier_location.id,
                "location_dest_id": self.warehouse.lot_stock_id.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "name": self.product.name,
                            "product_id": self.product.id,
                            "product_uom_qty": 5.0,
                            "product_uom": self.product.uom_id.id,
                            "location_id": supplier_location.id,
                            "location_dest_id": self.warehouse.lot_stock_id.id,
                            "price_unit": 0.0,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()
        picking.move_ids.quantity = 5.0
        picking.move_ids.picked = True
        picking.button_validate()
        layer = picking.move_ids.stock_valuation_layer_ids

        self.assertAlmostEqual(layer.value_in_currency, 500.0, places=2)
        self.assertAlmostEqual(self.product.standard_price_in_currency, 100.0, places=2)
        self.assertAlmostEqual(sum(self._layers().mapped("value_in_currency")), 700.0, places=2)

    def test_purchase_in_company_currency_with_manual_rate(self):
        """Compra en la moneda de la compañia recibida con cotizacion manual: la ficha usa esa cotizacion, igual que la capa."""
        usd = self.env.ref("base.USD")
        valuation_currency = usd if self.company.currency_id != usd else self.env.ref("base.EUR")
        valuation_currency.active = True
        # cotizacion del dia distinta de la manual
        self.env["res.currency.rate"].create(
            {
                "currency_id": valuation_currency.id,
                "rate": 0.2,
                "name": fields.Date.today(),
                "company_id": self.company.id,
            }
        )
        categ = self.categ.copy({"valuation_currency_id": valuation_currency.id})
        product = self._new_product("Producto comprado con cotizacion manual", categ)

        order = receive_purchase(self.env, product, 1.0, 2000.0, self.company.currency_id, currency_rate=0.25)

        layer = order.picking_ids.move_ids.stock_valuation_layer_ids
        self.assertAlmostEqual(layer.value_in_currency, 500.0, places=2)
        self.assertAlmostEqual(product.standard_price_in_currency, 500.0, places=2)

    def test_vendor_bill_price_difference_in_currency(self):
        """La factura con otro precio y con IVA ajusta el costo en moneda sin IVA y solo por lo que queda en stock."""
        if not has_purchase_journal(self.env):
            self.skipTest("La compañia no tiene diario de compras")
        product = self._new_product("Producto facturado con otro precio")
        bill = bill_with_price_difference(self.env, product)

        pdiff = bill.stock_valuation_layer_ids
        self.assertEqual(len(pdiff), 1)
        # (46 - 52.02) x 6 on hand, not the taxed total of the 10 billed (+36.40)
        self.assertAlmostEqual(pdiff.value_in_currency, -36.12, places=2)
        self.assertAlmostEqual(product.standard_price_in_currency, 46.0, places=2)
        layers = self.env["stock.valuation.layer"].search([("product_id", "=", product.id)])
        self.assertAlmostEqual(sum(layers.mapped("value_in_currency")), 46.0 * 6, places=2)
