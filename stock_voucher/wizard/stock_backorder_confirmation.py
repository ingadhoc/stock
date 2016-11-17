# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import api, models


class stock_backorder_confirmation(models.TransientModel):
    """
    we inherit to return report if book_required
    """
    _inherit = 'stock.backorder.confirmation'

    @api.multi
    def process(self):
        super(stock_backorder_confirmation, self).process()
        picking = self.env['stock.picking'].browse(
            self._context.get('active_id'))
        if picking.book_required:
            return picking.do_print_voucher()

    @api.multi
    def process_cancel_backorder(self):
        super(stock_backorder_confirmation, self).process_cancel_backorder()
        picking = self.env['stock.picking'].browse(
            self._context.get('active_id'))
        if picking.book_required:
            return picking.do_print_voucher()
