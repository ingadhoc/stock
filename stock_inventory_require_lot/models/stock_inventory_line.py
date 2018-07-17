from odoo import models, fields


class StockInventoryLine(models.Model):

    _inherit = 'stock.inventory.line'

    tracking = fields.Selection(
        related='product_id.tracking',
        readonly=True,
    )
