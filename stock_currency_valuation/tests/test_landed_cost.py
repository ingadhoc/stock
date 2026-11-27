from odoo.tests import tagged

from .common_valuation import LANDED_COST_RATE, PICKING_RATE, USD_RATE, CurrencyValuationCommon


@tagged("post_install", "-at_install")
class TestLandedCost(CurrencyValuationCommon):
    """Landed costs, also after a sale and validated with another company active."""

    def test_landed_costs_follow_the_receipt(self):
        """Each landed cost adds its USD to the layers, the product cost and the account, also after a sale."""
        # label, order currency, price, manual picking rate, manual landed cost rate
        cases = [
            ("compra en USD con cotizacion manual", self.usd, 100.0, PICKING_RATE, LANDED_COST_RATE),
            ("compra en USD con cotizacion automatica", self.usd, 100.0, 0.0, 0.0),
            ("compra en ARS y costo en destino con cotizacion manual", self.ars, 150000.0, 0.0, LANDED_COST_RATE),
        ]
        for label, currency, price, picking_rate, landed_cost_rate in cases:
            with self.subTest(label):
                lc_rate = landed_cost_rate or USD_RATE
                product = self._new_product(label)
                order = self._purchase([(product, 10, price)], currency)
                picking = self._receive(order, rate=picking_rate)

                with self.subTest("costo en destino de 150.000"):
                    landed_cost = self._landed_cost(picking, [150000.0], rate=landed_cost_rate)
                    self.assertAlmostEqual(
                        landed_cost.stock_valuation_layer_ids.value_in_currency, 150000.0 / lc_rate, places=2
                    )
                    self.assert_currency_valuation(product)

                with self.subTest("segundo costo en destino de 90.000 sin cotizacion"):
                    landed_cost = self._landed_cost(picking, [90000.0])
                    self.assertAlmostEqual(
                        landed_cost.stock_valuation_layer_ids.value_in_currency, 90000.0 / USD_RATE, places=2
                    )
                    self.assert_currency_valuation(product)

                with self.subTest("venta de 4"):
                    cost_usd = product.standard_price_in_currency
                    delivery = self._sell(product, 4)
                    self.assertAlmostEqual(
                        delivery.move_ids.stock_valuation_layer_ids.value_in_currency, -4 * cost_usd, places=2
                    )
                    self.assert_currency_valuation(product)

                with self.subTest("costo en destino de 60.000 despues de la venta"):
                    landed_cost = self._landed_cost(picking, [60000.0], rate=landed_cost_rate)
                    # only the 6 units still on hand take it: 36.000
                    self.assertAlmostEqual(
                        landed_cost.stock_valuation_layer_ids.value_in_currency, 36000.0 / lc_rate, places=2
                    )
                    self.assert_currency_valuation(product)

                with self.subTest("factura de proveedor un 10% mas cara"):
                    bill = self._bill(order, price * 1.1)
                    # the difference on the 6 units on hand: 10% of the price, in USD
                    difference_usd = price * 0.1 * 6 / (1.0 if currency == self.usd else USD_RATE)
                    pdiff = self._layers(product).filtered(
                        lambda layer, bill=bill: layer.account_move_line_id.move_id == bill
                    )
                    self.assertAlmostEqual(sum(pdiff.mapped("value_in_currency")), difference_usd, places=2)
                    self.assert_currency_valuation(product)

    def test_import_with_several_products_and_landed_costs(self):
        """An import of three products with landed costs of several lines and rates, split by quantity."""
        products = [self._new_product(name) for name in ("Producto A", "Producto B", "Producto C")]
        quantities = [10, 5, 5]
        order = self._purchase([(products[0], 10, 100.0), (products[1], 5, 200.0), (products[2], 5, 50.0)], self.usd)
        picking = self._receive(order, rate=PICKING_RATE)

        def check(landed_cost, total, rate):
            for product, quantity in zip(products, quantities):
                layers = landed_cost.stock_valuation_layer_ids.filtered(lambda layer, p=product: layer.product_id == p)
                # one layer per cost line, each rounded to the cent
                self.assertAlmostEqual(
                    sum(layers.mapped("value_in_currency")), total * quantity / 20 / rate, delta=0.01 * len(layers)
                )
            self.assert_currency_valuation(products)

        with self.subTest("costo en destino de dos lineas con cotizacion 1480"):
            check(self._landed_cost(picking, [100000.0, 40000.0], rate=LANDED_COST_RATE), 140000.0, LANDED_COST_RATE)

        with self.subTest("costo en destino de dos lineas con cotizacion 1500"):
            check(self._landed_cost(picking, [30000.0, 10000.0], rate=1500.0), 40000.0, 1500.0)

        with self.subTest("costo en destino validado con otra compania activa"):
            other_company = self.env["res.company"].create({"name": "Otra compania"})
            self.env.user.company_ids |= other_company
            # in the other company the category is not average cost
            self.categ_usd.with_company(other_company).property_cost_method = "standard"
            costs_before = [product.standard_price_in_currency for product in products]
            landed_cost = self._landed_cost(
                picking, [20000.0], rate=LANDED_COST_RATE, active_companies=other_company | self.company
            )
            check(landed_cost, 20000.0, LANDED_COST_RATE)
            for product, quantity, cost_before in zip(products, quantities, costs_before):
                self.assertAlmostEqual(
                    product.standard_price_in_currency,
                    cost_before + 20000.0 * quantity / 20 / LANDED_COST_RATE / quantity,
                    places=2,
                )
