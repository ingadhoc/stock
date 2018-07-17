from odoo import models, fields


class StockChangeProductQty(models.TransientModel):

    _inherit = 'stock.change.product.qty'

    tracking = fields.Selection(
        related='product_id.tracking',
        readonly=True
    )
