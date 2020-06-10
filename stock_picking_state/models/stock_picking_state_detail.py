##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class StockPickingStateDetail(models.Model):

    _name = 'stock.picking.state_detail'
    _description = 'stock.picking.state_detail'
    _order = 'sequence'

    name = fields.Char(
        copy=False,
        required=True,
    )
    sequence = fields.Integer(copy=False)
    picking_type = fields.Selection(
        required=True,
        selection=[
            ('internal', 'Internal'),
            ('outgoing', 'Outgoing'),
            ('incoming', 'Incoming'),
        ],
    )
    state = fields.Selection(
        string='Status',
        required=True,
        selection=[
            ('draft', 'Draft'),
            ('cancel', 'Cancelled'),
            ('waiting', 'Waiting Another Operation'),
            ('confirmed', 'Waiting'),
            ('assigned', 'Ready'),
            ('done', 'Done'),
        ],
    )
    picking_ids = fields.One2many(
        'stock.picking',
        'state_detail_id',
        'Pickings',
    )
