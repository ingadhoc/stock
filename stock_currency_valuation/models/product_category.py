from odoo import fields, models


class productCategory(models.Model):
    _inherit = "product.category"

    valuation_currency_id = fields.Many2one(
        "res.currency",
        string="Secondary Currency Valuation",
        company_dependent=True,
    )
