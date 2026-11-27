from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_receipt_rate(self):
        """Manual rate of the receipt when the purchase is in the valuation currency, or 0.

        With it the amount in currency is the purchase price itself and the company amount
        is that price divided by this rate, instead of the core's conversion at the date.
        """
        self.ensure_one()
        rate = self.picking_id.currency_rate
        if not rate or not self.purchase_line_id:
            return 0
        valuation_currency = self.with_company(self.company_id).valuation_currency_id
        if self.purchase_line_id.order_id.currency_id != valuation_currency:
            return 0
        return rate

    def _get_value_from_quotation(self, quantity, at_date=None):
        data = super()._get_value_from_quotation(quantity, at_date=at_date)
        if data["quantity"] and (rate := self._get_receipt_rate()):
            # The core converted the order price at the move date: redo it at the receipt rate
            order = self.purchase_line_id.order_id
            date_rate = self.env["res.currency"]._get_conversion_rate(
                order.currency_id, self.company_id.currency_id, self.company_id, self.date
            )
            data["value"] = data["value"] / date_rate / rate
        return data

    def _get_value_from_bill(self, aml):
        rate = self._get_receipt_rate()
        if rate and aml.currency_id == self.purchase_line_id.order_id.currency_id:
            return aml.company_id.currency_id.round(aml.price_subtotal / rate)
        return super()._get_value_from_bill(aml)
