##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class StockPickingStateDetail(models.Model):

    _name = 'stock.picking.state_detail'
    _description = 'stock.picking.state_detail'
    _order = 'sequence'

    name = fields.Char()
    sequence = fields.Integer()
    picking_type = fields.Selection(
        selection=[
            ('internal', 'Internal'),
            ('outgoing', 'Outgoing'),
            ('incoming', 'Incoming'),
        ],
    )
    state = fields.Selection(
        string='Status',
        store=True,
        selection=[
            ('draft', 'Draft'),
            ('cancel', 'Cancelled'),
            ('waiting', 'Waiting Another Operation'),
            ('confirmed', 'Waiting Availability'),
            ('partially_available', 'Partially Available'),
            ('assigned', 'Ready to Transfer'),
            ('done', 'Transferred'),
        ],
    )
    picking_ids = fields.One2many(
        'stock.picking',
        'state_detail_id',
        'Pickings',
    )
