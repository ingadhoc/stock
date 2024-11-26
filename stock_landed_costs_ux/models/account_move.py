# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def button_create_landed_costs(self):
        """Modifies the original method changing the price_unit of the landed_costs
        If the account.move has a different currency change from the one defined in the company,
        takes this one to calculate the price_unit
        """
        self.ensure_one()
        landed_costs_lines = self.line_ids.filtered(lambda line: line.is_landed_costs_line)
        rate_to_use = self.l10n_ar_currency_rate if self.l10n_ar_currency_rate else None
        landed_costs = self.env['stock.landed.cost'].with_company(self.company_id).create({
            'vendor_bill_id': self.id,
            'cost_lines': [(0, 0, {
                'product_id': l.product_id.id,
                'name': l.product_id.name,
                'account_id': l.product_id.product_tmpl_id.get_product_accounts()['stock_input'].id,
                'price_unit': self._compute_price_unit(l, rate_to_use),
                'split_method': l.product_id.split_method_landed_cost or 'equal',
            }) for l in landed_costs_lines],
        })
        action = self.env["ir.actions.actions"]._for_xml_id("stock_landed_costs.action_stock_landed_cost")
        return dict(action, view_mode='form', res_id=landed_costs.id, views=[(False, 'form')])

    def _compute_price_unit(self, landed_cost_line, rate_to_use):
        """Calculates the price_unit using the corresponding currency rate"""
        if rate_to_use:
            return landed_cost_line.price_subtotal * rate_to_use
        else:
            return landed_cost_line.currency_id._convert(
                landed_cost_line.price_subtotal,
                landed_cost_line.company_currency_id,
                landed_cost_line.company_id,
                self.invoice_date or fields.Date.context_today(self)
            )
