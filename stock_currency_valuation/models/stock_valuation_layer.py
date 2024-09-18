from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class StockValuationLayer(models.Model):

    _inherit = 'stock.valuation.layer'

    valuation_currency_id = fields.Many2one(related="categ_id.valuation_currency_id")
    unit_cost_in_currency = fields.Monetary('Unit Value in currency', compute="_compute_other_currency_values", currency_field='valuation_currency_id', store=True)
    value_in_currency = fields.Monetary('Total Value incurrency', compute="_compute_other_currency_values", currency_field='valuation_currency_id', store=True)
    product_tmpl_id = fields.Many2one(store=True)
    bypass_currency_valuation = fields.Boolean()

    @api.depends('categ_id', 'value', 'bypass_currency_valuation')
    def _compute_other_currency_values(self):
        for rec in self:
            if not rec.bypass_currency_valuation and rec.valuation_currency_id:
                rec.value_in_currency = rec.currency_id._convert(
                    from_amount=rec.value,
                    to_currency=rec.valuation_currency_id,
                    company=rec.company_id,
                    date=rec.create_date,
                )
                if rec.quantity:
                    rec.unit_cost_in_currency = abs(rec.value_in_currency / rec.quantity)
                else:
                    rec.unit_cost_in_currency = False
            else:
                rec.value_in_currency = False
                rec.unit_cost_in_currency = False
