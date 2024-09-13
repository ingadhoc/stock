##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, api, models, _

class StockPickingBatch(models.Model):
    _inherit = 'stock.picking.batch'

    voucher_ids = fields.One2many(
        'stock.picking.voucher',
        'batch_id',
        'Remitos',
        copy=False,
    )

    book_id = fields.Many2one(
        'stock.book',
        'Talonario',
        copy=False,
        ondelete='restrict',
        check_company=True
    )

    def assign_numbers(self, estimated_number_of_pages, book):
        self.ensure_one()
        list_of_vouchers = []
        for page in range(estimated_number_of_pages):
            list_of_vouchers.append({
                'name': book.sequence_id.next_by_id(),
                'book_id': book.id,
                'batch_id' : self.id,
            })
        self.env['stock.picking.voucher'].create(list_of_vouchers)
        self.message_post(body=_(
            'Números de remitos asignados: %s') % (self.vouchers))
        self.write({'book_id': book.id})
        return {
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking.batch',
                'view_mode': 'form',
                'res_id': self.id,
                'target': 'current',
            }