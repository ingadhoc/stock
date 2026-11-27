from odoo.tests import tagged

from .common_valuation import PICKING_RATE, CurrencyValuationCommon


@tagged("post_install", "-at_install")
class TestCurrencyValuationControls(CurrencyValuationCommon):
    """The controls of `assert_currency_valuation` pass on a sound receipt and catch each kind of drift."""

    def setUp(self):
        super().setUp()
        self.product = self._new_product("Producto controlado")
        order = self._purchase([(self.product, 10, 100.0)], self.usd)
        self.layer = self._receive(order, rate=PICKING_RATE).move_ids.stock_valuation_layer_ids
        self.valuation_line = self.layer.account_move_id.line_ids.filtered(
            lambda line: line.account_id == self.valuation_account
        )

    def test_sound_receipt_passes(self):
        self.assert_currency_valuation(self.product)

    def test_product_cost_apart_from_layers(self):
        self.product.with_context(disable_auto_svl=True).standard_price_in_currency = 90.0
        with self.assertRaisesRegex(AssertionError, "quantity on hand x USD cost"):
            self.assert_currency_valuation(self.product)

    def test_account_apart_from_layers(self):
        self.env.cr.execute(
            "UPDATE account_move_line SET amount_currency = amount_currency + 50 WHERE id = %s",
            [self.valuation_line.id],
        )
        self.valuation_line.invalidate_recordset(["amount_currency"])
        with self.assertRaisesRegex(AssertionError, "stock valuation account != USD of the layers"):
            self.assert_currency_valuation(self.product)

    def test_valuation_line_without_currency(self):
        self.env.cr.execute(
            "UPDATE account_move_line SET currency_id = %s, amount_currency = balance WHERE id = %s",
            [self.ars.id, self.valuation_line.id],
        )
        self.valuation_line.invalidate_recordset(["currency_id", "amount_currency"])
        with self.assertRaisesRegex(AssertionError, "stock valuation lines without USD"):
            self.assert_currency_valuation(self.product)

    def test_entry_apart_from_its_layers(self):
        order = self._purchase([(self.product, 10, 100.0)], self.usd)
        other_layer = self._receive(order, rate=PICKING_RATE).move_ids.stock_valuation_layer_ids
        other_line = other_layer.account_move_id.line_ids.filtered(
            lambda line: line.account_id == self.valuation_account
        )
        # same USD total in the account, moved from one entry to the other
        self.env.cr.execute(
            "UPDATE account_move_line SET amount_currency = amount_currency + 50 WHERE id = %s",
            [self.valuation_line.id],
        )
        self.env.cr.execute(
            "UPDATE account_move_line SET amount_currency = amount_currency - 50 WHERE id = %s", [other_line.id]
        )
        (self.valuation_line | other_line).invalidate_recordset(["amount_currency"])
        with self.assertRaisesRegex(AssertionError, "carries another USD amount than its layers"):
            self.assert_currency_valuation(self.product)
