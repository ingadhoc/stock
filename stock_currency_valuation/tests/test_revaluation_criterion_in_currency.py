from odoo.tests import tagged

from .common import TestStockCurrencyValuationCommon


@tagged("post_install", "-at_install")
class TestRevaluationCriterionInCurrency(TestStockCurrencyValuationCommon):
    """Which adjustments take a move out of the Stock Moves component of the report's
    variation, once the move's valuation carries TWO amounts.

    The base criterion in ``stock_account_ux`` is the delta in company currency. Here an
    adjustment that moved only the secondary amount also counts, because with
    ``_get_manual_value_in_currency`` in place it does change what the move is worth
    (task 64440, clarification Q2).
    """

    def setUp(self):
        super().setUp()
        self.report = self.env["stock_account.stock.valuation.report"]
        _picking, self.move = self._purchase_receipt(4, 25.0, self.INVERSE_D1, self.DAY_1)

    def _is_revalued(self):
        return self.move.id in self.report._get_revalued_move_ids(self._product())

    def _adjust(self, value, value_in_currency):
        return self.env["product.value"].create(
            {
                "move_id": self.move.id,
                "value": value,
                "value_in_currency": value_in_currency,
                "company_id": self.company.id,
            }
        )

    def test_move_without_adjustment_is_not_revalued(self):
        self.assertFalse(self._is_revalued())

    def test_currency_only_adjustment_is_a_revaluation(self):
        """Delta zero in company currency, non-zero in the secondary one. The base module
        would leave this move in Stock Moves; here it has to come out."""
        value_before = self.move.value
        currency_before = self.move.value_in_currency
        adjustment = self._adjust(value_before, currency_before + 5.0)

        self._assert_almost(adjustment.delta, 0.0)
        self._assert_almost(adjustment.delta_in_currency, 5.0)
        self.assertTrue(self._is_revalued())

    def test_company_currency_adjustment_is_still_a_revaluation(self):
        """The base criterion has to keep working."""
        self._adjust(self.move.value + 30.0, self.move.value_in_currency)
        self.assertTrue(self._is_revalued())

    def test_adjustment_with_no_delta_in_either_currency_is_not_a_revaluation(self):
        """An adjustment that moved nothing in either currency moved nothing, full stop."""
        adjustment = self._adjust(self.move.value, self.move.value_in_currency)

        self._assert_almost(adjustment.delta, 0.0)
        self._assert_almost(adjustment.delta_in_currency, 0.0)
        self.assertFalse(self._is_revalued())
