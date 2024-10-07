from odoo import models, fields


class productCategory(models.Model):

    _inherit = 'product.category'

    valuation_currency_id = fields.Many2one(
        'res.currency',
        string='Secondary Currency Valuation',
        company_dependent=True,
    )
