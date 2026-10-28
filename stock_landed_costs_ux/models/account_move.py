# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    def button_create_landed_costs(self):
        """Extends the original method changing the price_unit and the account of the landed costs.
        If the account.move has a currency rate, takes this one to calculate the price_unit
        """
        action = super().button_create_landed_costs()
        landed_costs = self.env["stock.landed.cost"].browse(action["res_id"])
        landed_costs_lines = self.line_ids.filtered(lambda line: line.is_landed_costs_line)
        rate_to_use = 1.0 / self.invoice_currency_rate if self.invoice_currency_rate else None
        sign = -1 if self.move_type == "in_refund" else 1
        # super() creates one cost line per landed costs line, in the same order
        for cost_line, line in zip(landed_costs.cost_lines, landed_costs_lines, strict=True):
            cost_line.write(
                {
                    "account_id": line.product_id.product_tmpl_id.get_product_accounts()["stock_valuation"].id,
                    "price_unit": sign * self._compute_price_unit(line, rate_to_use),
                }
            )
        return action

    def _compute_price_unit(self, landed_cost_line, rate_to_use):
        """Calculates the price_unit using the corresponding currency rate"""
        if rate_to_use:
            return landed_cost_line.price_subtotal * rate_to_use
        else:
            return landed_cost_line.currency_id._convert(
                landed_cost_line.price_subtotal,
                landed_cost_line.company_currency_id,
                landed_cost_line.company_id,
                self.invoice_date or fields.Date.context_today(self),
            )
