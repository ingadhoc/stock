from odoo import models, fields


class ProductCategory(models.Model):
    _inherit = 'product.category'

    removal_by_location_priority = fields.Boolean(
        'Force removal by location priority',
        default=True,
        help='If you select this option, the location priority would be used '
        'before the "Removal Strategy"',
    )
