##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class StockBackorderConfirmation(models.TransientModel):
    """
    we inherit to return report if book_required
    """
    _inherit = 'stock.backorder.confirmation'

    @api.multi
    def process(self):
        super(StockBackorderConfirmation, self).process()
        picking = self.env['stock.picking'].browse(
            # if we came, for eg, from a sale order, active_id would be the
            # sale order id
            # self._context.get('active_id'))
            # TODO we should also fix odoo methods
            self._context.get('picking_id'))
        if picking.book_required:
            return picking.do_print_voucher()

    @api.multi
    def process_cancel_backorder(self):
        super(StockBackorderConfirmation, self).process_cancel_backorder()
        picking = self.env['stock.picking'].browse(
            # if we came, for eg, from a sale order, active_id would be the
            # sale order id
            # self._context.get('active_id'))
            # TODO we should also fix odoo methods
            self._context.get('picking_id'))
        if picking.book_required:
            return picking.do_print_voucher()
