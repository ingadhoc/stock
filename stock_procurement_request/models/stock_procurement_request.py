# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models, api
from openerp.addons.procurement import procurement
# from openerp.exceptions import UserError


class StockProcurementRequest(models.Model):
    _name = "stock.procurement.request"
    _description = "Stock Procurement Request"

    name = fields.Char(
        required=True
    )
    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        default=lambda self: self.env.user.company_id,
    )
    group_id = fields.Many2one(
        'procurement.group',
        'Procurement Group',
    )
    procurement_ids = fields.One2many(
        'procurement.order',
        'procurement_request_id',
        'Procurements'
    )
    location_id = fields.Many2one(
        'stock.location',
        'Procurement Location',
        required=True,
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
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        'Warehouse',
        domain="[('company_id', '=', company_id)]",
        required=True,
        help="Warehouse to consider for the route selection"
    )
    priority = fields.Selection(
        procurement.PROCUREMENT_PRIORITIES,
        'Priority',
        required=True,
        select=True,
        default='1',
        # track_visibility='onchange'
    )
    date_planned = fields.Datetime(
        'Scheduled Date',
        required=True,
        select=True,
        default=lambda self: fields.Datetime.now(),
        # track_visibility='onchange'
    )

    @api.onchange('warehouse_id')
    def change_warehouse_id(self):
        self.location_id = self.warehouse_id.lot_stock_id

    @api.model
    def create(self, vals):
        if not vals.get('group_id'):
            group = self.group_id.create({})
            vals['group_id'] = group.id
        return super(StockProcurementRequest, self).create(vals)
