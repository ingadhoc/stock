from odoo.tests import tagged

from .common_valuation import PICKING_RATE, CurrencyValuationCommon


@tagged("post_install", "-at_install")
class TestCostMethodChange(CurrencyValuationCommon):
    """Cost method of the category changed with stock: Odoo empties and refills the stock with its own layers."""

    def test_cost_method_change_with_stock(self):
        """The stock goes out and back in at the USD cost of the product, with its USD in the journal entries."""
        categ = self._new_category("Cambia de metodo de costeo", valuation_currency_id=self.usd.id)
        product = self._new_product("Producto con stock", categ_id=categ.id)
        # cost in ARS at another rate than the system one, so a converted value shows up
        self._set_on_hand(product, 10, 100.0 * PICKING_RATE, 100.0)

        for label, cost_method in [("pasar a costo estandar", "standard"), ("volver a costo promedio", "average")]:
            with self.subTest(label):
                before = self._layers(product)
                categ.property_cost_method = cost_method
                added = self._layers(product) - before
                self.assertEqual(
                    sorted(added.mapped("value_in_currency")), [-1000.0, 1000.0], "empty and refill at the USD cost"
                )
                self.assertAlmostEqual(product.standard_price_in_currency, 100.0, places=2)
                self.assert_currency_valuation(product)
