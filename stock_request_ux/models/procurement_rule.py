##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models


class ProcurementRule(models.Model):
    _inherit = 'procurement.rule'

    def _get_stock_move_values(self, product_id, product_qty, product_uom,
                               location_id, name, origin, values, group_id):
        result = super(ProcurementRule, self)._get_stock_move_values(
            product_id, product_qty, product_uom, location_id, name, origin,
            values, group_id)
        stock_request_id = values.get('stock_request_id', False)
        if stock_request_id:
            # This it's because odoo clean the partner_id and origin in the
            # picking if has more than one stock request in the request order
            # https://github.com/odoo/odoo/blob/11.0/addons/
            # stock/models/stock_move.py#L696L703
            result['origin'] = self.env['stock.request'].browse(
                stock_request_id).order_id.name
        return result
