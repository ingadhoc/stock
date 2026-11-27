from odoo.tests import tagged

from .common_valuation import USD_RATE, CurrencyValuationCommon


@tagged("post_install", "-at_install")
class TestWithoutValuationCurrency(CurrencyValuationCommon):
    """A category without valuation currency keeps the native behavior."""

    def test_purchase_in_usd_without_valuation_currency(self):
        """The layer has no USD value and the entry keeps the amount in the order currency that Odoo puts."""
        categ = self._new_category("Sin moneda de valuacion")
        product = self._new_product("Producto sin moneda de valuacion", categ_id=categ.id)
        order = self._purchase([(product, 10, 100.0)], self.usd)
        layer = self._receive(order).move_ids.stock_valuation_layer_ids

        self.assertFalse(layer.value_in_currency)
        self.assertAlmostEqual(layer.value, 1000.0 * USD_RATE, places=2)
        valuation_line = layer.account_move_id.line_ids.filtered(lambda line: line.account_id == self.valuation_account)
        self.assertEqual(valuation_line.currency_id, self.usd)
        self.assertAlmostEqual(valuation_line.amount_currency, 1000.0, places=2)
