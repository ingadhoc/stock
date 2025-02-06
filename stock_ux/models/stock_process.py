##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class StockImmediateTransfer(models.TransientModel):
    _inherit = 'stock.immediate.transfer'

    def process(self):
        res = super().process()
        self.pick_ids.write({'return_lot_ids': self.pick_ids.move_line_ids.filtered(lambda l: l.qty_done > 0).mapped("lot_id")})
        return res
