# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import api, models


class stock_immediate_transfer(models.TransientModel):
    _inherit = 'stock.immediate.transfer'

    # @api.model
    # def default_get(self, fields):
    #     res = {}
    #     print ' xxxxxxxxxxx'
    #     active_id = self._context.get('picking_id')
    #     if active_id:
    #         res = {'pick_id': active_id}
    #     return res

    @api.multi
    def process(self):
        super(stock_immediate_transfer, self).process()
        picking = self.env['stock.picking'].browse(
            # if we came, for eg, from a sale order, active_id would be the
            # sale order id
            # self._context.get('active_id'))
            # TODO we should also fix odoo methods
            self._context.get('picking_id'))
        if picking.book_required:
            return picking.do_print_voucher()
