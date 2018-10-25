##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    vouchers = fields.Char(
        related='picking_id.vouchers',
        readonly=True,
    )

    def _action_cancel(self):
        res = super(StockMove, self)._action_cancel()
        self.mapped('picking_id').compute_declared_value()
        return res
