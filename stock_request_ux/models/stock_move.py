##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    request_order_id = fields.Many2one("stock.request.order", compute="_compute_request_order_id")

    @api.depends("stock_request_ids")
    def _compute_request_order_id(self):
        for rec in self:
            rec.request_order_id = rec.stock_request_ids.mapped("order_id")

    def _prepare_copy_allocation_vals(self, vals):
        # a split, a return and a push link the copy to its origin; a manual duplicate does not and takes no allocation
        if "move_orig_ids" not in vals and "origin_returned_move_id" not in vals:
            return []
        return super()._prepare_copy_allocation_vals(vals)

    # DEPRECATED def _split(self, qty, restrict_partner_id=False)
