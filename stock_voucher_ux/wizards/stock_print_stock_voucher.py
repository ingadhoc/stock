##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, api, models, _
from odoo.exceptions import UserError

class StockPrintStockVoucher(models.TransientModel):
    _inherit = 'stock.print_stock_voucher'

    def do_print_and_assign(self):
        # We override the method to avoid assignation
        if self.book_id.lines_per_voucher != 0:
            return {
                'actions': [
                    self.with_context(assign=True).do_print_voucher(),
                    {'type': 'ir.actions.client', 'tag': 'soft_reload'},
                ],
                'type': 'ir.actions.act_multi',
            }
        return super().do_print_and_assign()

    def do_print_voucher(self):
        self.printed = True
        if self.book_id:
            self.picking_id.write({'book_id': self.book_id.id})
        if not self.picking_id.book_id:
            raise UserError(_('You must enter a voucher book'))
        return self.picking_id.do_print_voucher()
