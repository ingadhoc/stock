# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields


class Users(models.Model):
    _inherit = 'res.users'

    restrict_locations = fields.Boolean(
        'Restrict Location', help="If True, you can set the location allowed")

    stock_location_ids = fields.Many2many(
        'stock.location',
        'location_security_stock_location_users',
        'user_id',
        'location_id',
        'Stock Locations')
