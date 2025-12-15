##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    pricelist_id = fields.Many2one(
        "product.pricelist",
        help="When 'Automatic Declare Value' is enabled and no sale order "
        "is linked to the picking, this pricelist will be used to suggest "
        "the declared value",
    )
    automatic_declare_value = fields.Boolean(
        help="When enabled, automatically suggest declared value based on "
        "product prices. The value will be calculated in the company's "
        "currency. Define a pricelist for pickings not linked to a sale order.",
    )
