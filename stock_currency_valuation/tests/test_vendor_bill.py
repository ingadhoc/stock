from odoo import Command
from odoo.tests import tagged

from .common_valuation import PICKING_RATE, CurrencyValuationCommon


@tagged("post_install", "-at_install")
class TestVendorBill(CurrencyValuationCommon):
    """Vendor bills at another price: `_prepare_pdiff_vals` and the exchange difference lines."""

    def test_bill_price_difference_in_currency(self):
        """The bill moves the USD of the layers, the product cost and the account only by its price difference."""
        tax = self.env["account.tax"].create(
            {"name": "IVA 21% compras", "amount": 21.0, "type_tax_use": "purchase", "company_id": self.company.id}
        )
        # label, manual receipt rate, units sold before the bill, bill price, bill line values,
        # expected difference in USD, expected USD cost
        cases = [
            ("factura mas barata", 0.0, 0, 90.0, {}, -100.0, 90.0),
            ("factura mas cara", 0.0, 0, 110.0, {}, 100.0, 110.0),
            ("factura mas cara con otra cotizacion que el remito", PICKING_RATE, 0, 110.0, {}, 100.0, 110.0),
            ("factura mas cara despues de vender 4", 0.0, 4, 110.0, {}, 60.0, 110.0),
            ("factura al mismo precio con IVA", 0.0, 0, 100.0, {"tax_ids": [Command.set(tax.ids)]}, 0.0, 100.0),
            ("factura al mismo precio con otra cotizacion que el remito", PICKING_RATE, 0, 100.0, {}, 0.0, 100.0),
            ("factura con todo ya vendido", 0.0, 10, 110.0, {}, 0.0, 100.0),
            ("factura con descuento del 100%", 0.0, 0, 100.0, {"discount": 100.0}, -1000.0, 0.0),
        ]
        for label, rate, sold, bill_price, line_vals, difference_usd, cost_usd in cases:
            with self.subTest(label):
                product = self._new_product(label)
                order = self._purchase([(product, 10, 100.0)], self.usd)
                self._receive(order, rate=rate)
                if sold:
                    self._sell(product, sold)
                bill = self._bill(order, bill_price, **line_vals)

                pdiff = self._layers(product).filtered(
                    lambda layer, bill=bill: layer.account_move_line_id.move_id == bill
                )
                self.assertAlmostEqual(sum(pdiff.mapped("value_in_currency")), difference_usd, places=2)
                self.assertAlmostEqual(product.standard_price_in_currency, cost_usd, places=2)
                self.assert_currency_valuation(product)
