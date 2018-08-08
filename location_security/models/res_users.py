##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    restrict_locations = fields.Boolean(
        help="If True, you can set the location allowed",
    )

    stock_location_ids = fields.Many2many(
        'stock.location',
        'location_security_stock_location_users',
        'user_id',
        'location_id',
        'Stock Locations',
    )
