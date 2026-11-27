from odoo.tests import tagged

from .common_valuation import PICKING_RATE, USD_RATE, CurrencyValuationCommon


@tagged("post_install", "-at_install")
class TestOutgoingAndReturns(CurrencyValuationCommon):
    """Outgoing moves and returns: the branches of `_compute_other_currency_values`."""

    def _check_step(self, product, operation, layer_usd, cost_usd):
        """Run `operation` and check the USD of the layers it adds and the USD cost it leaves."""
        before = self._layers(product)
        result = operation()
        added = self._layers(product) - before
        self.assertAlmostEqual(sum(added.mapped("value_in_currency")), layer_usd, places=2)
        self.assertAlmostEqual(product.standard_price_in_currency, cost_usd, places=2)
        self.assert_currency_valuation(product)
        return result

    def test_every_way_out_and_back(self):
        """Every way out, and the returns, move the USD of the product cost, which stays put."""
        product = self._new_product("Producto que entra y sale")
        # cost in ARS at another rate than the system one, so a converted value shows up
        product.standard_price = 100.0 * PICKING_RATE
        product.standard_price_in_currency = 100.0
        delivery = self.env["stock.picking"]

        with self.subTest("ajuste de inventario a 20"):
            self._check_step(product, lambda: self._set_on_hand(product, 20), 2000.0, 100.0)
        with self.subTest("venta de 5"):
            delivery = self._check_step(product, lambda: self._sell(product, 5), -500.0, 100.0)
        with self.subTest("devolucion de 2 de la venta"):
            self._check_step(product, lambda: self._return(delivery, 2), 200.0, 100.0)
        with self.subTest("desecho de 3"):
            self._check_step(product, lambda: self._scrap(product, 3), -300.0, 100.0)
        with self.subTest("salida sin pedido de 4"):
            self._check_step(product, lambda: self._move_without_order(product, 4), -400.0, 100.0)
        with self.subTest("ajuste de inventario a 7"):
            self._check_step(product, lambda: self._set_on_hand(product, 7), -300.0, 100.0)
        with self.subTest("ingreso sin pedido y sin precio de 5"):
            self._check_step(product, lambda: self._move_without_order(product, 5, incoming=True), 500.0, 100.0)

        receipt = self.env["stock.picking"]
        # (12 x 100 + 10 x 120) / 22
        cost_after_purchase = 2400.0 / 22
        with self.subTest("compra de 10 a 120 USD con cotizacion manual"):
            order = self._purchase([(product, 10, 120.0)], self.usd)
            receipt = self._check_step(
                product, lambda: self._receive(order, rate=PICKING_RATE), 1200.0, cost_after_purchase
            )
        with self.subTest("devolucion de 4 de la compra"):
            self._check_step(product, lambda: self._return(receipt, 4), -4 * cost_after_purchase, cost_after_purchase)

    def test_negative_stock_covered_by_a_receipt(self):
        """A sale without stock goes out at the current cost; the receipt that covers it leaves the cost of the receipt."""
        product = self._new_product("Producto vendido sin stock")
        product.standard_price = 80.0 * USD_RATE
        product.standard_price_in_currency = 80.0

        with self.subTest("venta de 5 sin stock"):
            self._check_step(product, lambda: self._sell(product, 5), -400.0, 80.0)
        with self.subTest("compra de 10 a 100 USD que cubre lo vendido"):
            order = self._purchase([(product, 10, 100.0)], self.usd)
            # the receipt enters at 1000 and the 5 sold are revalued from 80 to 100
            self._check_step(product, lambda: self._receive(order), 900.0, 100.0)

    def test_return_of_a_purchase_return(self):
        """Returning goods sent back to the vendor brings them in at the USD cost they left with."""
        product = self._new_product("Producto devuelto dos veces")
        order = self._purchase([(product, 10, 100.0)], self.usd)
        receipt = self._receive(order, rate=PICKING_RATE)
        returned = self.env["stock.picking"]

        with self.subTest("devolucion de 4 al proveedor"):
            returned = self._check_step(product, lambda: self._return(receipt, 4), -400.0, 100.0)
        with self.subTest("devolucion de esa devolucion"):
            self._check_step(product, lambda: self._return(returned, 4), 400.0, 100.0)
