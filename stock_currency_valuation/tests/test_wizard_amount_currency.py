from collections import defaultdict

from odoo.tests import tagged

from .common import TestStockCurrencyValuationCommon


@tagged("post_install", "-at_install")
class TestWizardAmountCurrency(TestStockCurrencyValuationCommon):
    """The manual valuation entry carries the amount in the secondary currency, and adds
    up to zero in BOTH currencies.

    That double balance is the assertion that matters: an entry that balances in company
    currency and not in the other one posts without complaint and leaves the secondary
    valuation quietly wrong.
    """

    def setUp(self):
        super().setUp()
        # Periodic valuation: with real-time the receipt is booked on validation and the
        # wizard would rule the move out as already valued.
        self.category.with_company(self.company).property_valuation = "periodic"
        self.journal = self.env["account.journal"].search(
            [("type", "=", "general"), ("company_id", "=", self.company.id)], limit=1
        )

    def _assert_balanced_per_currency(self, entry):
        """The entry balances in company currency AND, separately, within each currency its
        lines are expressed in.

        Summing ``amount_currency`` across lines of DIFFERENT currencies is meaningless
        even when it happens to come out at zero, so it is grouped first. Note every
        ``account.move.line`` has a ``currency_id`` —it is required and defaults to the
        company's— so "no currency" is not a thing; a line untouched by this module simply
        stays in the company currency.
        """
        self._assert_almost(sum(entry.line_ids.mapped("balance")), 0.0)
        by_currency = defaultdict(float)
        for line in entry.line_ids:
            by_currency[line.currency_id] += line.amount_currency
        for currency, total in by_currency.items():
            self._assert_almost(total, 0.0, msg=f"The entry does not balance in {currency.name}")

    def _wizard_for(self, moves):
        return (
            self.env["stock.move.valuation"]
            .with_context(default_move_ids=moves.ids)
            .create({"journal_id": self.journal.id})
        )

    # -- Escenarios donde la moneda secundaria NO aplica ------------------------
    # stock_account_ux es auto_install, así que corre en muchas bases sin este
    # módulo, y este módulo corre en bases donde no todas las categorías usan
    # moneda secundaria. Los tres casos de abajo son los que este cambio abre.

    def _periodic_category(self, name, valuation_currency=None):
        category = self.env["product.category"].create({"name": name, "property_cost_method": "average"})
        scoped = category.with_company(self.company)
        scoped.property_valuation = "periodic"
        if valuation_currency:
            scoped.valuation_currency_id = valuation_currency
        return category

    def _receipt_of(self, product, qty, price_unit):
        """Recepción validada de un producto arbitrario, sin pasar por la orden de compra
        (el helper de common está atado al producto del fixture)."""
        picking = self.env["stock.picking"].create(
            {
                "partner_id": self.vendor.id,
                "picking_type_id": self.picking_type_in.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_uom_qty": qty,
                            "product_uom": self.uom_unit.id,
                            "location_id": self.supplier_location.id,
                            "location_dest_id": self.stock_location.id,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()
        move = picking.move_ids
        move.quantity = qty
        move.value_manual = qty * price_unit
        move.picked = True
        picking.button_validate()
        return move

    def test_category_without_secondary_currency_books_no_amount_currency(self):
        """A category with no valuation currency has to produce exactly what the base
        module produces on its own: no currency on the line, no secondary amount."""
        category = self._periodic_category("SCV plain")
        product = self.env["product.product"].create(
            {
                "name": "Producto sin moneda",
                "is_storable": True,
                "categ_id": category.id,
                "uom_id": self.uom_unit.id,
            }
        )
        move = self._receipt_of(product, 4, 25000.0)
        self.assertFalse(product.with_company(self.company).valuation_currency_id)

        wizard = self._wizard_for(move)
        vals_list = wizard._get_account_move_line_vals()

        self.assertTrue(vals_list, "The draft has to have lines.")
        for vals in vals_list:
            self.assertNotIn("currency_id", vals)
            self.assertNotIn("amount_currency", vals)

    def test_valuation_currency_equal_to_the_company_currency(self):
        """When the category is valued in the company's own currency, Odoo requires
        ``amount_currency`` to equal ``balance``. Posting has to work, not raise."""
        category = self._periodic_category("SCV same currency", self.company_currency)
        product = self.env["product.product"].create(
            {
                "name": "Producto misma moneda",
                "is_storable": True,
                "categ_id": category.id,
                "uom_id": self.uom_unit.id,
            }
        )
        move = self._receipt_of(product, 4, 25000.0)
        self.assertEqual(product.with_company(self.company).valuation_currency_id, self.company_currency)

        wizard = self._wizard_for(move)
        wizard.action_post()

        entry = move.account_move_id
        self.assertTrue(entry, "Posting must not raise when both currencies coincide.")
        self._assert_almost(sum(entry.line_ids.mapped("balance")), 0.0)
        for line in entry.line_ids:
            self._assert_almost(line.amount_currency, line.balance)

    def test_draft_has_no_single_currency_when_lines_disagree(self):
        """Two products valued in DIFFERENT secondary currencies in one draft: a single
        total states nothing, so it is left empty and the view hides it. The per-line
        amounts stay."""
        other_currency = self.env["res.currency"].create({"name": "SCO", "symbol": "O$", "rounding": 0.01})
        self.env["res.currency.rate"].create(
            {
                "name": self.DAY_1,
                "rate": self.RATE_D2,
                "currency_id": other_currency.id,
                "company_id": self.company.id,
            }
        )
        other_category = self._periodic_category("SCV other currency", other_currency)
        other_product = self.env["product.product"].create(
            {
                "name": "Producto otra moneda",
                "is_storable": True,
                "categ_id": other_category.id,
                "uom_id": self.uom_unit.id,
            }
        )
        other_move = self._receipt_of(other_product, 4, 25000.0)
        _picking, move = self._purchase_receipt(4, 25000.0, self.INVERSE_D1, self.DAY_1)

        wizard = self._wizard_for(move + other_move)

        currencies = wizard.line_ids.valuation_currency_id
        self.assertEqual(len(currencies), 2, "The draft has to gather two currencies.")
        self.assertFalse(wizard.valuation_currency_id)
