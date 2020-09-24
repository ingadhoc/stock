##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class StockMoveLine(models.Model):

    _inherit = 'stock.move.line'

    origin = fields.Char(
        related='move_id.picking_id.origin',
        # we store so we can group
        store=True,
    )
