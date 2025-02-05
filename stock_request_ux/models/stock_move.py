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

    # DEPRECATED def _split(self, qty, restrict_partner_id=False)
