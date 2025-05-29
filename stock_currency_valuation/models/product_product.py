from odoo import fields, models


class productProduct(models.Model):
    _inherit = "product.product"

    valuation_currency_id = fields.Many2one(
        related="categ_id.valuation_currency_id",
    )
    standard_price_in_currency = fields.Float(
        "Cost in currency",
        company_dependent=True,
        groups="base.group_user",
        help="Cost of the product expressed in the secondary currency defined on the product category. Used for inventory valuation and cost calculations in that currency.",
    )
