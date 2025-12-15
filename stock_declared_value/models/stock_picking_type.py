##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    pricelist_id = fields.Many2one(
        "product.pricelist",
        "Pricelist",
        help='If you choose a pricelist, "Automatic Declare Value" is'
        " enabled on company and no sale order is found linked to the"
        " picking, we will suggest declared value using this pricelist",
    )
    automatic_declare_value = fields.Boolean(
        help="The declared value will be in the currency of the company",
    )
