##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class StockBackorderConfirmation(models.TransientModel):
    """
    we inherit to return report if book_required
    """
    _inherit = 'stock.backorder.confirmation'

    def process(self):
        super().process()
        pickings = self.env['stock.picking'].browse(
            # if we came, for eg, from a sale order, active_id would be the
            # sale order id
            # self._context.get('active_id'))
            # TODO we should also fix odoo methods
            self._context.get('picking_ids')).filtered('book_required')
        if pickings:
            return {
                'actions': [
                    {'type': 'ir.actions.act_window_close'},
                    pickings.do_print_voucher(),
                ],
                'type': 'ir.actions.act_multi',
            }

    def process_cancel_backorder(self):
        super().process_cancel_backorder()
        pickings = self.env['stock.picking'].browse(
            # if we came, for eg, from a sale order, active_id would be the
            # sale order id
            # self._context.get('active_id'))
            # TODO we should also fix odoo methods
            self._context.get('picking_ids')).filtered('book_required')
        if pickings:
            return {
                'actions': [
                    {'type': 'ir.actions.act_window_close'},
                    pickings.do_print_voucher(),
                ],
                'type': 'ir.actions.act_multi',
            }
