from odoo.tests import tagged

from .common import TestStockCurrencyValuationCommon


@tagged("post_install", "-at_install")
class TestPreviousValueInCurrency(TestStockCurrencyValuationCommon):
    """``previous_value_in_currency`` / ``delta_in_currency``: the secondary-currency twins
    of the pair ``stock_account_ux`` records in company currency.

    The previous value is captured when the adjustment is created and never recomputed:
    once it is saved the adjustment has already been applied to the move and to the
    product's cost, so there is nothing left to subtract from.
    """

    def _last_product_value(self, domain):
        return self.env["product.value"].search(domain, order="date desc, id desc", limit=1)

    def test_delta_in_currency_of_a_price_change(self):
        product = self._product()
        product.standard_price_in_currency = 100.0
        first = self._last_product_value([("product_id", "=", product.id), ("move_id", "=", False)])
        self.assertTrue(first, "Changing the secondary cost has to record a product.value.")
        self._assert_almost(first.value_in_currency, 100.0)

        product.standard_price_in_currency = 130.0
        second = self._last_product_value([("product_id", "=", product.id), ("move_id", "=", False)])
        self.assertNotEqual(second, first, "The second change has to record its own adjustment.")

        # The previous value comes off the previous adjustment, not off the product, which
        # by now already carries the new cost.
        self._assert_almost(second.previous_value_in_currency, 100.0)
        self._assert_almost(second.delta_in_currency, 30.0)

    def test_previous_value_in_currency_of_a_move_adjustment(self):
        _picking, move = self._purchase_receipt(4, 25.0, self.INVERSE_D1, self.DAY_1)
        before = move.value_in_currency
        self.assertTrue(before, "The receipt has to be valued in the secondary currency.")

        move.value_manual_in_currency = before + 7.0

        adjustment = self._last_product_value([("move_id", "=", move.id)])
        self.assertTrue(adjustment, "Adjusting the secondary amount has to record a product.value.")
        # On a move the previous value is the move's own, and the delta is what the
        # adjustment moved — both in the move's total, not per unit.
        self._assert_almost(adjustment.previous_value_in_currency, before)
        self._assert_almost(adjustment.delta_in_currency, 7.0)

    def test_delta_in_currency_is_not_recomputed_afterwards(self):
        """The captured value has to stay pinned: recomputing it later would read the cost
        the adjustment itself installed and the delta would collapse to zero."""
        product = self._product()
        product.standard_price_in_currency = 100.0
        product.standard_price_in_currency = 130.0
        adjustment = self._last_product_value([("product_id", "=", product.id), ("move_id", "=", False)])

        adjustment.invalidate_recordset(["delta_in_currency"])

        self._assert_almost(adjustment.previous_value_in_currency, 100.0)
        self._assert_almost(adjustment.delta_in_currency, 30.0)
