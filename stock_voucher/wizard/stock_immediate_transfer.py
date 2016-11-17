# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import api, models


class stock_immediate_transfer(models.TransientModel):
    _inherit = 'stock.immediate.transfer'

    @api.multi
    def process(self):
        super(stock_immediate_transfer, self).process()
        picking = self.env['stock.picking'].browse(
            self._context.get('active_id'))
        if picking.book_required:
            return picking.do_print_voucher()
