from freezegun import freeze_time
from odoo import Command, fields

from .common import TestStockCurrencyValuationCommon


class TestReceiptBeforeBill(TestStockCurrencyValuationCommon):
    """A receipt of an order in the valuation currency, validated before its vendor bill.

    Without a bill the core values the receipt from the order, converted to company
    currency at the rate of the move date. The value in currency has to give back the
    order amount, not that converted amount at the rate typed on the receipt.
    """

    def _foreign_order_receipt(self, qty, price_unit, inverse_rate, date_str):
        with freeze_time(date_str):
            order = self.env["purchase.order"].create(
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
                                "date_planned": date_str,
                            }
                        )
                    ],
                }
            )
            order.button_confirm()
            picking = order.picking_ids
            picking.inverse_currency_rate = inverse_rate
            move = picking.move_ids
            move.quantity = qty
            move.picked = True
            picking.button_validate()
            self.assertEqual(picking.state, "done")
            return order, move

    def test_receipt_before_bill_keeps_order_amount(self):
        # Order for 100 in currency, received on day 2 (rate 1200) with the rate of day 1
        # (1000) typed on the receipt.
        order, move = self._foreign_order_receipt(
            qty=10, price_unit=10, inverse_rate=self.INVERSE_D1, date_str=self.DAY_2
        )
        self.assertAlmostEqual(move.value, 120000, places=2)
        self.assertAlmostEqual(move.value_in_currency, 100.00, places=2)

        # Once the bill of day 1 is posted, the value comes from it and the receipt rate
        # applies: the value in currency is still the order amount.
        with freeze_time(self.DAY_2):
            order.action_create_invoice()
            bill = order.invoice_ids
            bill.invoice_date = fields.Date.to_date(self.DAY_1)
            bill.action_post()
        self.assertAlmostEqual(move.value, 100000, places=2)
        self.assertAlmostEqual(move.value_in_currency, 100.00, places=2)
