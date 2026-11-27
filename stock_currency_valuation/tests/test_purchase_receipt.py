from odoo.tests import tagged

from .common_valuation import EUR_RATE, PICKING_RATE, USD_RATE, CurrencyValuationCommon


@tagged("post_install", "-at_install")
class TestPurchaseReceipt(CurrencyValuationCommon):
    """Purchase receipts: the path where Odoo 18 changed the receipt price the most."""

    def test_receipt_values_layer_and_cost_in_currency(self):
        """A receipt enters the layer and the product cost with the same USD unit price."""
        box = self.env["uom.uom"].create(
            {
                "name": "Caja x6",
                "category_id": self.env.ref("uom.product_uom_categ_unit").id,
                "uom_type": "bigger",
                "factor_inv": 6.0,
            }
        )
        # label, order currency, quantity, price, purchase uom, manual rate, expected USD per unit
        cases = [
            ("compra en USD con cotizacion automatica", self.usd, 10, 100.0, None, 0.0, 100.0),
            ("compra en USD con cotizacion manual", self.usd, 10, 100.0, None, PICKING_RATE, 100.0),
            ("compra en ARS con cotizacion automatica", self.ars, 10, 150000.0, None, 0.0, 150000.0 / USD_RATE),
            (
                "compra en ARS con cotizacion manual",
                self.ars,
                10,
                150000.0,
                None,
                PICKING_RATE,
                150000.0 / PICKING_RATE,
            ),
            ("compra en cajas de 6 con cotizacion manual", self.usd, 2, 600.0, box, PICKING_RATE, 100.0),
            ("compra en cajas de 6 con cotizacion automatica", self.usd, 2, 600.0, box, 0.0, 100.0),
            ("compra en EUR con valuacion en USD", self.eur, 10, 100.0, None, 0.0, 100.0 * EUR_RATE / USD_RATE),
        ]
        for label, currency, quantity, price, uom, rate, unit_usd in cases:
            with self.subTest(label):
                product = self._new_product(label)
                line = (product, quantity, price, uom) if uom else (product, quantity, price)
                order = self._purchase([line], currency)
                move = self._receive(order, rate=rate).move_ids

                self.assertAlmostEqual(
                    move.stock_valuation_layer_ids.value_in_currency, unit_usd * move.product_qty, places=2
                )
                self.assertAlmostEqual(product.standard_price_in_currency, unit_usd, places=2)
                self.assert_currency_valuation(product)

    def test_bill_before_receipt_with_backorder(self):
        """Billed before receiving, each partial receipt enters at the USD price of the order."""
        for label, bill_rate in [
            ("factura con la cotizacion del sistema", 0.0),
            ("factura con cotizacion manual", PICKING_RATE),
        ]:
            with self.subTest(label):
                product = self._new_product(label, purchase_method="purchase")
                order = self._purchase([(product, 10, 100.0)], self.usd)
                self._bill(order, 100.0, rate=bill_rate)

                with self.subTest("recepcion parcial de 4"):
                    move = self._receive(order, quantity=4).move_ids
                    self.assertAlmostEqual(move.stock_valuation_layer_ids.value_in_currency, 400.0, places=2)
                    self.assertAlmostEqual(product.standard_price_in_currency, 100.0, places=2)
                    self.assert_currency_valuation(product)

                with self.subTest("backorder de 6"):
                    move = self._receive(order).move_ids
                    self.assertAlmostEqual(move.stock_valuation_layer_ids.value_in_currency, 600.0, places=2)
                    self.assertAlmostEqual(product.standard_price_in_currency, 100.0, places=2)
                    self.assert_currency_valuation(product)

    def test_two_moves_of_the_same_product(self):
        """With stock on hand, each move of the same product enters the average at its own price.

        Not covered until product defines it: adding quantity to a receipt already done
        (Odoo 18 passes `forced_qty` as a (lot, quantity) pair and the module fails).
        """
        product = self._new_product("Producto con stock previo")
        self._set_on_hand(product, 10, 100.0 * PICKING_RATE, 100.0)
        order = self._purchase([(product, 5, 100.0), (product, 5, 120.0)], self.usd)
        picking = self._receive(order, rate=PICKING_RATE)

        self.assertEqual(sorted(picking.move_ids.stock_valuation_layer_ids.mapped("value_in_currency")), [500.0, 600.0])
        # (10 x 100 + 5 x 100 + 5 x 120) / 20
        self.assertAlmostEqual(product.standard_price_in_currency, 105.0, places=2)
        self.assert_currency_valuation(product)
