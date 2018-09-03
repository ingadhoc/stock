##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class StockMoveLine(models.Model):

    _inherit = 'stock.move.line'

    block_additional_quantiy = fields.Boolean(
        related='picking_id.block_additional_quantiy',
        readonly=True,
        default=True,
    )

    @api.constrains('qty_done')
    def _check_quantity(self):
        for pack in self:
            if pack.picking_id.block_additional_quantiy and pack.\
                    product_qty < pack.qty_done:
                raise ValidationError(_(
                    'You can not transfer a product without a move on the '
                    'picking!'))

    # @api.model
    # def create(self, vals):
    #     op = super(StockMoveLine, self).create(vals)
    #     if op.fresh_record
    #     and op.picking_id.picking_type_id.block_additional_quantiy:
    #         raise ValidationError(_(
    #             'You can not add operations to this picking'))
    #     return op
