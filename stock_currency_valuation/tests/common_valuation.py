from dateutil.relativedelta import relativedelta
from odoo import Command, fields
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import (
    ValuationReconciliationTestCommon,
)

# ARS per unit of each currency. Round values, apart from each other, so every
# layer can be followed by hand and a wrong rate is easy to spot.
USD_RATE = 1400.0
EUR_RATE = 1500.0
PICKING_RATE = 1450.0
LANDED_COST_RATE = 1480.0


class CurrencyValuationCommon(ValuationReconciliationTestCommon):
    """Company in ARS that values its stock in USD in real time, with its own accounts.

    Every test checks after each step the three controls of the module
    (`assert_currency_valuation`): layers against the product cost, layers against
    the stock valuation account, and each journal entry against its layers.
    """

    # the generic chart, so the suite does not need the Argentinian localization installed
    chart_template = "generic_coa"

    @classmethod
    def setup_independent_company(cls, **kwargs):
        ars = cls.env.ref("base.ARS")
        ars.active = True
        # the generic chart sets USD while loading; saas_client_account would reject it for Argentina
        cls.env = cls.env(context=dict(cls.env.context, skip_currency_constraint=True))
        return super().setup_independent_company(country_id=cls.env.ref("base.ar").id, currency_id=ars.id, **kwargs)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.today()
        cls.company = cls.env.company
        # continental accounting, as the customers of the module
        cls.company.anglo_saxon_accounting = False
        cls.ars = cls.company.currency_id
        rate_date = cls.today - relativedelta(years=1)
        cls.usd = cls.setup_other_currency("USD", rates=[(rate_date, 1 / USD_RATE)])
        cls.eur = cls.setup_other_currency("EUR", rates=[(rate_date, 1 / EUR_RATE)])
        cls.warehouse = cls.company_data["default_warehouse"]
        cls.valuation_account = cls.company_data["default_account_stock_valuation"]
        cls.stock_journal = cls.company_data["default_journal_misc"]
        cls.expense_account = cls.company_data["default_account_expense"]
        cls.categ_usd = cls._new_category("Valuada en USD", valuation_currency_id=cls.usd.id)
        cls.landed_cost_product = cls.env["product.product"].create(
            {
                "name": "Flete de importacion",
                "type": "service",
                "landed_cost_ok": True,
                "split_method_landed_cost": "by_quantity",
                "property_account_expense_id": cls.expense_account.id,
            }
        )

    # ------------------------------------------------------------------ data

    @classmethod
    def _new_category(cls, name, **vals):
        """Average cost category valued in real time with the stock accounts of the company."""
        return cls.env["product.category"].create(
            {
                "name": name,
                "property_cost_method": "average",
                "property_valuation": "real_time",
                "property_stock_valuation_account_id": cls.valuation_account.id,
                "property_stock_account_input_categ_id": cls.company_data["default_account_stock_in"].id,
                "property_stock_account_output_categ_id": cls.company_data["default_account_stock_out"].id,
                "property_stock_journal": cls.stock_journal.id,
                **vals,
            }
        )

    def _new_product(self, name, **vals):
        return (
            self.env["product.product"]
            .create(
                {
                    "name": name,
                    "is_storable": True,
                    "categ_id": self.categ_usd.id,
                    "supplier_taxes_id": [Command.clear()],
                    "taxes_id": [Command.clear()],
                    **vals,
                }
            )
            .with_company(self.company)
        )

    def _set_on_hand(self, product, quantity, cost_ars=None, cost_usd=None):
        """Set the stock on hand with an inventory adjustment, at the given product cost if any."""
        if cost_ars is not None:
            product.standard_price = cost_ars
            product.standard_price_in_currency = cost_usd
        self.env["stock.quant"].with_context(inventory_mode=True).create(
            {"product_id": product.id, "location_id": self.warehouse.lot_stock_id.id, "inventory_quantity": quantity}
        ).action_apply_inventory()

    def _purchase(self, lines, currency):
        """Confirmed purchase without taxes; `lines` is a list of (product, qty, price[, uom])."""
        order = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "currency_id": currency.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": line[0].id,
                            "product_qty": line[1],
                            "price_unit": line[2],
                            "product_uom": (line[3] if len(line) > 3 else line[0].uom_po_id).id,
                            "taxes_id": [Command.clear()],
                        }
                    )
                    for line in lines
                ],
            }
        )
        order.button_confirm()
        return order

    def _receive(self, order, rate=0.0, quantity=None):
        """Validate the pending receipt of `order`, with a manual rate (ARS per USD) if given.

        With a `quantity` below the ordered one, the rest stays in a backorder.
        """
        picking = order.picking_ids.filtered(lambda p: p.state not in ("done", "cancel"))
        if rate:
            picking.inverse_currency_rate = rate
        for move in picking.move_ids:
            move.quantity = quantity if quantity is not None else move.product_uom_qty
        picking.move_ids.picked = True
        picking.with_context(skip_backorder=True).button_validate()
        return picking

    def _bill(self, order, price_unit, rate=0.0, **line_vals):
        """Post the vendor bill of `order` at `price_unit`, with a manual rate (ARS per unit) if given."""
        order.action_create_invoice()
        bill = order.invoice_ids.filtered(lambda move: move.state == "draft")
        bill.invoice_date = self.today
        if rate:
            bill.invoice_currency_rate = 1 / rate
        bill.invoice_line_ids.write({"price_unit": price_unit, **line_vals})
        bill.action_post()
        return bill

    def _landed_cost(self, pickings, amounts, rate=0.0, active_companies=None):
        """Validate a landed cost in ARS with one cost line per amount, split by quantity.

        `active_companies` validates it as a user with those companies active, the first one current.
        """
        LandedCost = self.env["stock.landed.cost"]
        if active_companies:
            LandedCost = LandedCost.with_context(allowed_company_ids=active_companies.ids)
        landed_cost = LandedCost.create(
            {
                "company_id": self.company.id,
                "picking_ids": [Command.set(pickings.ids)],
                "account_journal_id": self.stock_journal.id,
                "cost_lines": [
                    Command.create(
                        {
                            "product_id": self.landed_cost_product.id,
                            "price_unit": amount,
                            "split_method": "by_quantity",
                            "account_id": self.expense_account.id,
                        }
                    )
                    for amount in amounts
                ],
            }
        )
        if rate:
            landed_cost.inverse_currency_rate = rate
        landed_cost.compute_landed_cost()
        landed_cost.button_validate()
        return landed_cost

    def _sell(self, product, quantity):
        """Confirm a sale and validate its delivery."""
        # sale_stock auto installs with the dependencies of the module (sale comes with product_replenishment_cost)
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "order_line": [
                    Command.create({"product_id": product.id, "product_uom_qty": quantity, "price_unit": 250000.0})
                ],
            }
        )
        order.action_confirm()
        picking = order.picking_ids
        picking.move_ids.quantity = quantity
        picking.move_ids.picked = True
        picking.button_validate()
        return picking

    def _return(self, picking, quantity):
        """Return `quantity` of a done picking and validate the return."""
        wizard = (
            self.env["stock.return.picking"].with_context(active_id=picking.id, active_model="stock.picking").create({})
        )
        wizard.product_return_moves.quantity = quantity
        returned = wizard._create_return()
        returned.move_ids.quantity = quantity
        returned.move_ids.picked = True
        returned.button_validate()
        return returned

    def _move_without_order(self, product, quantity, incoming=False):
        """Validate a receipt from a vendor or a delivery to a customer without order nor price."""
        picking_type = self.warehouse.in_type_id if incoming else self.warehouse.out_type_id
        partner_location = self.env.ref(
            "stock.stock_location_suppliers" if incoming else "stock.stock_location_customers"
        )
        stock_location = self.warehouse.lot_stock_id
        source, destination = (partner_location, stock_location) if incoming else (stock_location, partner_location)
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": source.id,
                "location_dest_id": destination.id,
                "move_ids": [
                    Command.create(
                        {
                            "name": product.name,
                            "product_id": product.id,
                            "product_uom_qty": quantity,
                            "product_uom": product.uom_id.id,
                            "location_id": source.id,
                            "location_dest_id": destination.id,
                        }
                    )
                ],
            }
        )
        picking.action_confirm()
        picking.move_ids.quantity = quantity
        picking.move_ids.picked = True
        picking.button_validate()
        return picking

    def _scrap(self, product, quantity):
        scrap = self.env["stock.scrap"].create(
            {"product_id": product.id, "scrap_qty": quantity, "location_id": self.warehouse.lot_stock_id.id}
        )
        scrap.action_validate()
        return scrap

    def _revalue(self, product, added_value):
        """Validate a manual revaluation of `added_value` ARS against the expense account."""
        self.env["stock.valuation.layer.revaluation"].with_company(self.company).create(
            {
                "product_id": product.id,
                "company_id": self.company.id,
                "added_value": added_value,
                "reason": "Revaluacion",
                "account_id": self.expense_account.id,
                "account_journal_id": self.stock_journal.id,
            }
        ).action_validate_revaluation()
        return self._layers(product).sorted("id")[-1]

    def _layers(self, product):
        return self.env["stock.valuation.layer"].search(
            [("product_id", "=", product.id), ("company_id", "=", self.company.id)]
        )

    # ------------------------------------------------------------ controls

    def assert_currency_valuation(self, products):
        """The three controls of the module, valid after any stock operation."""
        for product in products:
            product = product.with_company(self.company)
            layers = self._layers(product)
            # each layer rounds its USD value to the cent
            delta = 0.01 * max(len(layers), 1)
            layers_usd = sum(layers.mapped("value_in_currency"))

            # the product cost is rounded to the price precision: half a unit of it per unit on hand
            cost_digits = self.env["decimal.precision"].precision_get("Product Price")
            cost_rounding = abs(product.quantity_svl) * 0.5 * 10**-cost_digits
            self.assertAlmostEqual(
                layers_usd,
                product.quantity_svl * product.standard_price_in_currency,
                delta=delta + cost_rounding,
                msg=f"{product.name}: USD of the layers != quantity on hand x USD cost of the product",
            )

            valuation_lines = self.env["account.move.line"].search(
                [
                    ("product_id", "=", product.id),
                    ("account_id", "=", self.valuation_account.id),
                    ("parent_state", "=", "posted"),
                ]
            )
            self.assertEqual(
                valuation_lines.filtered(lambda line: line.currency_id != self.usd),
                self.env["account.move.line"],
                f"{product.name}: stock valuation lines without USD",
            )
            self.assertAlmostEqual(
                sum(valuation_lines.mapped("amount_currency")),
                layers_usd,
                delta=delta,
                msg=f"{product.name}: USD of the stock valuation account != USD of the layers",
            )

            for entry in layers.account_move_id:
                entry_layers = layers.filtered(lambda layer, entry=entry: layer.account_move_id == entry)
                entry_lines = valuation_lines.filtered(lambda line, entry=entry: line.move_id == entry)
                self.assertAlmostEqual(
                    sum(entry_lines.mapped("amount_currency")),
                    sum(entry_layers.mapped("value_in_currency")),
                    places=2,
                    msg=f"{product.name}: entry {entry.display_name} carries another USD amount than its layers",
                )
