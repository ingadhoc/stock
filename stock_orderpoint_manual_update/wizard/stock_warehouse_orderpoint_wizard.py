from odoo import fields, models, _
from odoo.osv import expression


class StockWarehouseOrderpointWizard(models.TransientModel):
    _name = 'stock.warehouse.orderpoint.wizard'
    _description = 'Stock Warehouse Orderpoint Wizard'

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    product_ids = fields.Many2many('product.product', string='Product')
    category_ids = fields.Many2many('product.category', string='Product Category')
    supplier_ids = fields.Many2many('res.partner', string='Vendor', check_company=True)
    filter_by_main_supplier = fields.Boolean(string="Filter by Main Vendor")
    location_ids = fields.Many2many('stock.location', string="Location")

    def action_confirm(self):
        ctx = self._context.copy()
        ctx.update({
            'filter_products': self.product_ids.ids,
            'filter_categories': self.category_ids.ids,
            'filter_suppliers': self.supplier_ids.ids,
            'filter_locations': self.location_ids.ids,
        })
        action = self.with_context(ctx).env['stock.warehouse.orderpoint']._get_orderpoint_action()
        orderpoint_domain = self._get_orderpoint_domain()
        orderpoints = self.env['stock.warehouse.orderpoint'].with_context(active_test=False).search(orderpoint_domain)
        orderpoints._compute_qty_to_order()
        orderpoints.update_qty_forecast()
        orderpoints._compute_rotation()
        orderpoints._change_review_toggle_negative()
        action['domain'] = expression.AND([
            action.get('domain', '[]'),
            orderpoint_domain,
        ])
        return action

    def _get_orderpoint_domain(self):
        orderpoint_domain = []
        if self.product_ids:
            orderpoint_domain.append(('product_id', 'in', self.product_ids.ids))
        if self.category_ids:
            orderpoint_domain.append(('product_category_id', 'in', self.category_ids.ids))
        if self.filter_by_main_supplier:
            orderpoint_domain.append(('supplier_id.partner_id', 'in', self.supplier_ids.ids))
        elif self.supplier_ids:
            orderpoint_domain.append(('product_id.seller_ids.partner_id', 'in', self.supplier_ids.ids))
        if self.location_ids:
            orderpoint_domain.append(('location_id', 'in', self.location_ids.ids))
        return orderpoint_domain
