##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class StockMove(models.Model):
    _inherit = 'stock.move'

    picking_user_id = fields.Many2one(
        'res.users',
        related='picking_id.user_id',
        string="Picking Responsible",
    )
