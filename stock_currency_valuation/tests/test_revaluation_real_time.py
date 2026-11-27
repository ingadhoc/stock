from odoo.tests import tagged

from .common_valuation import USD_RATE, CurrencyValuationCommon


@tagged("post_install", "-at_install")
class TestRevaluationRealTime(CurrencyValuationCommon):
    """Manual revaluation with real time valuation: the module copies the native wizard whole."""

    def test_revaluation_up_and_down(self):
        """A revaluation up and another down move the USD of the layer, the product cost and the account."""
        product = self._new_product("Producto revaluado")
        self._set_on_hand(product, 10, 100.0 * USD_RATE, 100.0)

        with self.subTest("revaluacion en mas de 50.000"):
            layer = self._revalue(product, 50000.0)
            self.assertAlmostEqual(layer.value_in_currency, 50000.0 / USD_RATE, places=2)
            self.assertAlmostEqual(product.standard_price_in_currency, 100.0 + 5000.0 / USD_RATE, places=2)
            self.assert_currency_valuation(product)

        with self.subTest("revaluacion en menos de 20.000"):
            layer = self._revalue(product, -20000.0)
            self.assertAlmostEqual(layer.value_in_currency, -20000.0 / USD_RATE, places=2)
            self.assertAlmostEqual(product.standard_price_in_currency, 100.0 + 3000.0 / USD_RATE, places=2)
            self.assert_currency_valuation(product)
