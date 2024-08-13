##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, api, models


class StockPrintStockVoucher(models.TransientModel):
    _inherit = 'stock.print_stock_voucher'

    def do_print_and_assign(self):
        # We override the method to avoid assignation
        if self.book_id.lines_per_voucher != 0:
            return {
                'actions': [
                    {'type': 'ir.actions.act_window_close'},
                        self.with_context(assign=True).do_print_voucher(),
                ],
                'type': 'ir.actions.act_multi'
            }
        return super().do_print_and_assign()
