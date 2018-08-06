##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class StockPicking(models.Model):

    _inherit = 'stock.picking'

    state_detail_id = fields.Many2one(
        'stock.picking.state_detail',
        string='State Detail',
        track_visibility='onchange',
        index=True,
        copy=False,
    )
