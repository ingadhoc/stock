from freezegun import freeze_time
from odoo import Command
from odoo.addons.stock_currency_valuation.tests.common import TestStockCurrencyValuationCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestPurchaseInValuationCurrency(TestStockCurrencyValuationCommon):
    """A purchase in the valuation currency, received with a manual rate: the value in
    currency is the purchase price and the company amount is that price at the manual
    rate, not the price converted at the date and then divided by the manual rate."""

    def _receive_purchase_in_currency(self, qty, price_unit, inverse_rate, date_str):
        with freeze_time(date_str):
            po = self.env["purchase.order"].create(
                {
                    "partner_id": self.vendor.id,
                    "currency_id": self.secondary_currency.id,
                    "order_line": [
                        Command.create(
                            {
                                "product_id": self.product.id,
                                "product_qty": qty,
                                "price_unit": price_unit,
                                "product_uom_id": self.uom_unit.id,
                            }
                        )
                    ],
                }
            )
            po.button_confirm()
            picking = po.picking_ids
            if inverse_rate:
                picking.inverse_currency_rate = inverse_rate
            picking.move_ids.quantity = qty
            picking.move_ids.picked = True
            picking.button_validate()
            return po, picking.move_ids

    def _post_bill(self, po, date_str):
        with freeze_time(date_str):
            po.action_create_invoice()
            bill = po.invoice_ids
            bill.invoice_date = date_str
            bill.action_post()
            return bill

    def test_manual_rate_values_the_receipt_at_that_rate(self):
        # Day 3 rate is 1500; the receipt says 1000
        po, move = self._receive_purchase_in_currency(10, 10.0, self.INVERSE_D1, self.DAY_3)

        self._assert_almost(move.value, 100000.0)
        self._assert_almost(move.value_in_currency, 100.0)
        self._assert_almost(self._product().standard_price_in_currency, 10.0)

        self._post_bill(po, self.DAY_3)
        move.invalidate_recordset(["value", "value_in_currency"])
        self._assert_almost(move.value, 100000.0)
        self._assert_almost(move.value_in_currency, 100.0)

    def test_without_manual_rate_the_date_rate_applies(self):
        _po, move = self._receive_purchase_in_currency(10, 10.0, 0, self.DAY_3)

        self._assert_almost(move.value, 150000.0)
        self._assert_almost(move.value_in_currency, 100.0)
