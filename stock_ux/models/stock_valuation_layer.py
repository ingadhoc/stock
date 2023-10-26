# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools
from odoo.tools import float_compare, float_is_zero


class StockValuationLayer(models.Model):

    _inherit = 'stock.valuation.layer'

    secondary_currency_id = fields.Many2one(related='company_id.secondary_currency_id')
    secondary_currency_unit_cost = fields.Monetary('Unit Value(SC)', compute='_compute_secondary_currency_amounts', currency_field='secondary_currency_id', compute_sudo=True)
    secondary_currency_value = fields.Monetary('Total Value (SC)', compute='_compute_secondary_currency_amounts', currency_field='secondary_currency_id', compute_sudo=True)
    secondary_currency_remaining_value = fields.Monetary('Remaining Value (SC)', compute='_compute_secondary_currency_amounts', currency_field='secondary_currency_id', compute_sudo=True)
    secondary_currency_price_diff_value = fields.Monetary('Invoice value correction with invoice currency (SC)', compute='_compute_secondary_currency_amounts', currency_field='secondary_currency_id', compute_sudo=True)

    @api.depends('secondary_currency_id', 'secondary_currency_unit_cost', 'secondary_currency_value', 'secondary_currency_remaining_value', 'secondary_currency_price_diff_value')
    def _compute_secondary_currency_amounts(self):
        # por performance usamos get_conversion_date en vez de convert, para pedirlo solo una vez porque la fecha es la misma
        with_secondary_currency = self.filtered('secondary_currency_id')
        (self - with_secondary_currency).secondary_currency_unit_cost = False
        (self - with_secondary_currency).secondary_currency_value = False
        (self - with_secondary_currency).secondary_currency_remaining_value = False
        (self - with_secondary_currency).secondary_currency_price_diff_value = False
        for rec in with_secondary_currency:
            rate = rec.currency_id._get_conversion_rate(rec.currency_id, rec.secondary_currency_id, rec.company_id, rec.create_date)
            rec.secondary_currency_unit_cost = rec.secondary_currency_id.round(rec.unit_cost * rate) if rec.unit_cost else 0.0
            rec.secondary_currency_value = rec.secondary_currency_id.round(rec.value * rate) if rec.value else 0.0
            rec.secondary_currency_remaining_value = rec.secondary_currency_id.round(rec.remaining_value * rate) if rec.remaining_value else 0.0
            rec.secondary_currency_price_diff_value = rec.secondary_currency_id.round(rec.price_diff_value * rate) if rec.price_diff_value else 0.0
