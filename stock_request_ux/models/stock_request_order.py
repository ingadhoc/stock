##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models


class StockRequestOrder(models.Model):
    _inherit = "stock.request.order"
    _order = "id desc"

    warehouse_id = fields.Many2one(
        change_default=True,
    )

    @api.onchange("route_id")
    def onchange_route_id(self):
        for line in self.stock_request_ids:
            if self.route_id.id in line.route_ids.ids:
                line.route_id = self.route_id.id
