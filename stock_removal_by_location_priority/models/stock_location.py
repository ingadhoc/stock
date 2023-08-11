from odoo import fields, models


class StockLocation(models.Model):
    _inherit = 'stock.location'

    removal_strategy_method = fields.Char(related='removal_strategy_id.method')
    removal_priority = fields.Integer(
        default=10,
        help='Priority used on stock removal if "Force removal by location "'
        'priority" is configured on product category.',
    )
