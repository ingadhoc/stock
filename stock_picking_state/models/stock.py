# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields


class StockPickingStateDetail(models.Model):
    _name = 'stock.picking.state_detail'
    _order = 'sequence'

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence')
    picking_type = fields.Selection(
        selection=[
            ('internal', 'Internal'),
            ('outgoing', 'Outgoing'),
            ('incoming', 'Incoming'),
        ],
        string="Picking Type",
    )
    state = fields.Selection(
        store=True,
        selection=[
            ('draft', 'Draft'),
            ('cancel', 'Cancelled'),
            ('waiting', 'Waiting Another Operation'),
            ('confirmed', 'Waiting Availability'),
            ('partially_available', 'Partially Available'),
            ('assigned', 'Ready to Transfer'),
            ('done', 'Transferred'),
        ], string='Status'
    )
    picking_ids = fields.One2many(
        'stock.picking',
        'state_detail_id',
        'Pickings')


class StockPicking(models.Model):

    _inherit = 'stock.picking'

    state_detail_id = fields.Many2one(
        'stock.picking.state_detail',
        string='State Detail',
        track_visibility='onchange',
        select=True
    )

    code = fields.Selection(
        related='picking_type_id.code',
        readonly=True,)
