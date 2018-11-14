##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class StockPickingType(models.Model):

    _inherit = 'stock.picking.type'

    block_additional_quantity = fields.Boolean(
        string="Block additional quantity",
        help="Do not allow to confirm pickings with more quantity than the "
        "initial demand and also block pickings duplication",
        default=True,
    )

    block_picking_deletion = fields.Boolean(
        help="Do not allow to remove pickings",
        default=True,
    )

    block_manual_lines = fields.Boolean(
        string="Block force availability",
        help="Do not allow to confirm pickings with more quantity than the "
        "reserved one. This will only apply for moves where origin location "
        "is not of type 'supplier', 'customer', 'inventory', 'production'",
    )
