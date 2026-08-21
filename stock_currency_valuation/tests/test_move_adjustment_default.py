from odoo.tests import tagged

from .common import TestStockCurrencyValuationCommon


@tagged("post_install", "-at_install")
class TestMoveAdjustmentDefault(TestStockCurrencyValuationCommon):
    """Default of a ``product.value`` recorded ON A MOVE with no amount given.

    There ``value`` is the move's TOTAL value, not a unit price: the model docstring in
    ``stock_account`` says so, and ``stock.move._get_manual_value`` writes it straight into
    ``move.value``. Defaulting to the product's ``standard_price`` wrote a unit price where
    a total belongs, and left the move valued at the cost of a single unit.

    Reachable through ``stock.move.value_manual_in_currency``, whose inverse records an
    adjustment carrying only the secondary amount.
    """

    def test_move_adjustment_defaults_to_the_moves_own_value(self):
        _picking, move = self._purchase_receipt(4, 25.0, self.INVERSE_D1, self.DAY_1)
        product = self._product()
        # The two candidate defaults have to differ, or the assertion below proves nothing.
        self.assertNotAlmostEqual(
            product.standard_price,
            move.value,
            msg="The unit cost and the move total must differ for this test to mean anything.",
        )
        self._assert_almost(move.value, 100.0)

        self.env["product.value"].create({"move_id": move.id, "company_id": self.company.id})

        # The adjustment carried no amount, so it took the move's own value: the move keeps
        # being worth what it was worth, not one unit's cost.
        self._assert_almost(move.value, 100.0)

    def test_currency_only_adjustment_keeps_the_company_value(self):
        """Setting only the secondary amount by hand must not touch the value in company
        currency — that is what makes it a currency-only adjustment."""
        _picking, move = self._purchase_receipt(4, 25.0, self.INVERSE_D1, self.DAY_1)
        value_before = move.value

        move.value_manual_in_currency = move.value_in_currency + 7.0

        self._assert_almost(move.value, value_before)
