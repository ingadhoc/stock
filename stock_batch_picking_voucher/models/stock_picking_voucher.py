##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class StockPickingVoucher(models.Model):
    _inherit = 'stock.picking.voucher'

    batch_id = fields.Many2one(
        'stock.picking.batch',
        'Batch',
        ondelete='cascade',
        index=True,
    )

    picking_id = fields.Many2one(
        'stock.picking',
        'Picking',
        ondelete='cascade',
        required=False,
        index=True,
    )

    @api.constrains('picking_id', 'batch_id')
    def _check_picking_id_required(self):
        for record in self:
            if not record.batch_id and not record.picking_id:
                raise ValidationError("Al crear un voucher debe estar ligado a una trasnferencia o lote de transferencias")
