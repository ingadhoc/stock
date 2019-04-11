##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    stock_request_order_ids = fields.One2many(
        comodel_name='stock.request.order',
        string='Stock Request Orders',
        compute='_compute_stock_request_order_ids',
    )
    stock_request_order_count = fields.Integer(
        'Stock Request Order #',
        compute='_compute_stock_request_order_ids',
    )

    @api.depends('move_lines')
    def _compute_stock_request_order_ids(self):
        for rec in self:
            rec.stock_request_order_ids = rec.move_lines.mapped(
                'stock_request_ids.order_id')
            rec.stock_request_order_count = len(
                rec.stock_request_order_ids)

    def action_view_stock_order_request(self):
        """
        :return dict: dictionary value for created view
        """
        action = self.env.ref(
            'stock_request.stock_request_order_action').read()[0]

        request_orders = self.mapped('stock_request_order_ids')
        if len(request_orders) > 1:
            action['domain'] = [('id', 'in', request_orders.ids)]
        elif request_orders:
            action['views'] = [
                (self.env.ref('stock_request.stock_request_order_form').id,
                 'form')]
            action['res_id'] = request_orders.id
        return action
