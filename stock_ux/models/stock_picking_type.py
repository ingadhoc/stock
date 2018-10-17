##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class StockPickingType(models.Model):

    _inherit = 'stock.picking.type'

    block_additional_quantity = fields.Boolean(
        string="Block additional quantity",
        help="Restrict additional quantity",
        default=True,
    )

    block_picking_deletion = fields.Boolean(
        help="Do not allow to remove pickings",
        default=True,
    )

    block_manual_lines = fields.Boolean(
        default=True,
        help="Do not allow manual lines (for eg. to block force availability)",
    )
