##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model_create_multi
    def create(self, vals_list):
        if vals_list and vals_list[0].get('picking_type_id') and self.env['stock.picking.type'].browse(vals_list[0]['picking_type_id']).code == 'outgoing':
            sale_line_qty_ret = self.env['sale.order.line'].browse(vals_list[0]['sale_line_id']).quantity_returned
            vals_list[0]['product_uom_qty'] -= sale_line_qty_ret
        res = super().create(vals_list)
        return res
