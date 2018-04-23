# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from openerp import models, api


class StockPackOperationLot(models.Model):

    _inherit = 'stock.pack.operation.lot'

    @api.multi
    def set_all_done(self):
        for rec in self:
            rec.qty = rec.qty_todo
            rec.operation_id.qty_done = sum(
                rec.operation_id.pack_lot_ids.mapped('qty'))
        return self[0].operation_id.split_lot()
