# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api
from odoo.addons.procurement import procurement
# from odoo.exceptions import UserError


class StockProcurementRequest(models.Model):
    _name = "stock.procurement.request"
    _description = "Stock Procurement Request"

    state = fields.Selection([
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('running', 'Running'),
        ('done', 'Done')],
        compute='_compute_state',
        help='* Draft state if not procurements\n'
        '* Done state if all procurements are on done or cancelled state'
        '* Running state if at least one procurement on state different from '
        'done or cancelled'
    )
    name = fields.Char(
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        default=lambda self: self.env.user.company_id,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    group_id = fields.Many2one(
        'procurement.group',
        'Procurement Group',
        copy=False,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    procurement_ids = fields.One2many(
        'procurement.order',
        'procurement_request_id',
        'Procurements',
    )
    location_id = fields.Many2one(
        'stock.location',
        'Procurement Location',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    route_ids = fields.Many2many(
        'stock.location.route',
        'stock_location_route_procurement_request',
        'procurement_request_id',
        'route_id',
        'Preferred Routes',
        help="Preferred route to be followed by the procurement order. "
        "Usually copied from the generating document (SO) but could be set "
        "up manually.",
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        'Warehouse',
        domain="[('company_id', '=', company_id)]",
        required=True,
        help="Warehouse to consider for the route selection",
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    priority = fields.Selection(
        procurement.PROCUREMENT_PRIORITIES,
        'Priority',
        required=True,
        select=True,
        default='1',
        # track_visibility='onchange'
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    date_planned = fields.Datetime(
        'Scheduled Date',
        required=True,
        select=True,
        default=lambda self: fields.Datetime.now(),
        # track_visibility='onchange',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )

    @api.multi
    @api.depends('procurement_ids.state')
    def _compute_state(self):
        for rec in self:
            if not rec.procurement_ids:
                state = 'draft'
            elif all([x.state == 'done' for x in rec.procurement_ids]):
                state = 'done'
            elif all([x.state == 'cancel' for x in rec.procurement_ids]):
                state = 'cancel'
            else:
                state = 'running'
            rec.state = state

    @api.onchange('warehouse_id')
    def change_warehouse_id(self):
        self.location_id = self.warehouse_id.lot_stock_id

    @api.model
    def create(self, vals):
        if not vals.get('group_id'):
            warehouse = self.warehouse_id.browse(vals.get('warehouse_id'))
            # setamos al group el partner del warehouse para que se propague
            # a los pickings
            group = self.group_id.create(
                {'partner_id': warehouse.partner_id.id})
            vals['group_id'] = group.id
        return super(StockProcurementRequest, self).create(vals)
