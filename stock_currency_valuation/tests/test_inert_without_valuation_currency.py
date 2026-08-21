from odoo.tests import tagged

from .common import TestStockCurrencyValuationCommon


@tagged("post_install", "-at_install")
class TestInertWithoutValuationCurrency(TestStockCurrencyValuationCommon):
    """With NO category using a secondary valuation currency, this module has to be inert:
    the report, the closing and the wizard must give exactly what they give without it
    installed.

    That is the majority scenario — ``stock_account_ux`` is ``auto_install`` and runs in
    plenty of databases where nobody values stock in a second currency — so a regression
    here is a regression for everyone.
    """

    def setUp(self):
        super().setUp()
        # No category has a valuation currency: the fixture's one is cleared.
        self.category.with_company(self.company).valuation_currency_id = False
        self.category.with_company(self.company).property_valuation = "periodic"
        self.assertFalse(self._product().with_company(self.company).valuation_currency_id)
        self.journal = self.env["account.journal"].search(
            [("type", "=", "general"), ("company_id", "=", self.company.id)], limit=1
        )

    def test_secondary_twins_return_nothing(self):
        accounts_by_product = self.company._get_accounts_by_product()
        self.assertFalse(self.company.stock_value_in_currency(accounts_by_product))
        self.assertFalse(self.company.stock_accounting_value_in_currency(accounts_by_product))

    def test_closing_vals_are_not_annotated(self):
        """``_annotate_valuation_vals`` has to hand the vals back untouched: no
        ``currency_id``, no ``amount_currency``, so the entry is byte for byte what the base
        module would build."""
        self._purchase_receipt(4, 25000.0, self.INVERSE_D1, self.DAY_1)
        accounts_by_product = self.company._get_accounts_by_product()
        vals_list = [
            {"account_id": 1, "name": "x", "debit": 100.0, "credit": 0.0, "product_id": False},
            {"account_id": 2, "name": "x", "debit": 0.0, "credit": 100.0, "product_id": False},
        ]

        result = self.company._annotate_valuation_vals(vals_list, accounts_by_product)

        for vals in result:
            self.assertNotIn("currency_id", vals)
            self.assertNotIn("amount_currency", vals)

    def test_closing_entry_stays_in_company_currency(self):
        self._purchase_receipt(4, 25000.0, self.INVERSE_D1, self.DAY_1)
        self.company.action_close_stock_valuation()
        entry = self.env["account.move"].search([("company_id", "=", self.company.id)], order="id desc", limit=1)
        self.assertTrue(entry, "The closing has to produce an entry.")
        for line in entry.line_ids:
            self.assertEqual(line.currency_id, self.company_currency)
            self._assert_almost(line.amount_currency, line.balance)

    def test_wizard_entry_stays_in_company_currency(self):
        _picking, move = self._purchase_receipt(4, 25000.0, self.INVERSE_D1, self.DAY_1)
        wizard = (
            self.env["stock.move.valuation"]
            .with_context(default_move_ids=move.ids)
            .create({"journal_id": self.journal.id})
        )
        for vals in wizard._get_account_move_line_vals():
            self.assertNotIn("currency_id", vals)
            self.assertNotIn("amount_currency", vals)
        # And the draft offers no secondary total.
        self.assertFalse(wizard.valuation_currency_id)

    def test_revaluation_criterion_falls_back_to_the_base(self):
        """The ``_is_revaluation`` override must not change the base answer: an adjustment
        with no delta in company currency is not a revaluation when there is no secondary
        currency to look at."""
        report = self.env["stock_account.stock.valuation.report"]
        _picking, move = self._purchase_receipt(4, 25000.0, self.INVERSE_D1, self.DAY_1)
        self.env["product.value"].search([("move_id", "=", move.id)]).unlink()
        self.env["product.value"].create({"move_id": move.id, "value": move.value, "company_id": self.company.id})

        self.assertNotIn(move.id, report._get_revalued_move_ids(self._product()))
