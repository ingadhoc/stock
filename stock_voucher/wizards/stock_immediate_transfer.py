##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class StockImmediateTransfer(models.TransientModel):
    _inherit = 'stock.immediate.transfer'

    def process(self):
        res = super().process()
        pickings = self.env['stock.picking'].browse(
            # if we came, for eg, from a sale order, active_id would be the
            # sale order id
            # self._context.get('active_id'))
            # TODO we should also fix odoo methods
            self._context.get('picking_ids')).filtered(lambda p: p.book_required and p.voucher_ids)
        # solo viene con vouchers en entrega total, sin backorder
        # si hay backorder se termina imprimiendo desde el backorder
        # confirmation
        if pickings:
            if isinstance(res, bool):
                res = {'type': 'ir.actions.act_window_close'}
            return {
                'actions': [
                    res,
                    pickings.do_print_voucher(),
                ],
                'type': 'ir.actions.act_multi',
            }
        else:
            return res
