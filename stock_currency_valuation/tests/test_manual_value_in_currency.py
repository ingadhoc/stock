from odoo.tests import tagged

from .common import TestStockCurrencyValuationCommon


@tagged("post_install", "-at_install")
class TestManualValueInCurrency(TestStockCurrencyValuationCommon):
    """A manual adjustment of a move's value in the SECONDARY currency has to reach the
    move, the same way the core's ``_get_manual_value`` makes the company-currency one
    reach it.

    Before this, the "New Value in Currency" field of the "Adjust Valuation" dialog wrote
    a ``product.value`` that no computation read: ``_set_value`` always recomputed
    ``value_in_currency`` off the AVCO or the picking rate, so the user edited the amount,
    saved, and the move went on being worth the same.
    """

    def test_manual_value_in_currency_reaches_the_move(self):
        _picking, move = self._purchase_receipt(4, 25.0, self.INVERSE_D1, self.DAY_1)
        computed = move.value_in_currency
        self.assertTrue(computed, "The receipt has to be valued in the secondary currency.")
        target = computed + 5.0

        move.value_manual_in_currency = target

        self._assert_almost(move.value_in_currency, target)

    def test_manual_value_in_currency_survives_a_recompute(self):
        """It has to hold across later ``_set_value`` calls, as the company-currency manual
        value does — otherwise the next recompute silently undoes the user's correction."""
        _picking, move = self._purchase_receipt(4, 25.0, self.INVERSE_D1, self.DAY_1)
        target = move.value_in_currency + 5.0
        move.value_manual_in_currency = target

        move._set_value()

        self._assert_almost(move.value_in_currency, target)

    def test_manual_value_in_currency_of_zero_is_honoured(self):
        """An explicit zero is a correction, not an absence: the lookup returns ``None``
        when there is no adjustment precisely so that zero can mean zero."""
        _picking, move = self._purchase_receipt(4, 25.0, self.INVERSE_D1, self.DAY_1)
        self.assertTrue(move.value_in_currency)

        self.env["product.value"].create(
            {
                "move_id": move.id,
                "value": move.value,
                "value_in_currency": 0.0,
                "company_id": self.company.id,
            }
        )

        self._assert_almost(move.value_in_currency, 0.0)
        # And the value in company currency is untouched: this is a currency-only change.
        self.assertTrue(move.value)

    def test_a_move_with_no_adjustment_keeps_the_computed_value(self):
        _picking, move = self._purchase_receipt(4, 25.0, self.INVERSE_D1, self.DAY_1)
        computed = move.value_in_currency

        move._set_value()

        self._assert_almost(move.value_in_currency, computed)
