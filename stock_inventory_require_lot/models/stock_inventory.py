from openerp import models, fields


class StockInventoryLine(models.Model):

    _inherit = 'stock.inventory.line'

    tracking = fields.Selection(related='product_id.tracking', readonly=True,)


class StockChangeProductQty(models.TransientModel):

    _inherit = 'stock.change.product.qty'

    tracking = fields.Selection(
        related='product_id.tracking')
