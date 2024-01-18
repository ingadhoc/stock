from odoo import fields, models, _


class StockWarehouseOrderpointWizard(models.TransientModel):
    _name = 'stock.warehouse.orderpoint.wizard'
    _description = 'Stock Warehouse Orderpoint Wizard'

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    partner_ids = fields.Many2many('res.partner', string='Vendor', check_company=True)
    category_ids = fields.Many2many('product.category', string='Product Category')
    product_ids = fields.Many2many('product.product', string='Product')

    def action_confirm(self):
        ctx = self._context.copy()
        suppliers = self.env['product.supplierinfo'].search([('partner_id', 'in', self.partner_ids.ids)])
        ctx.update({
            'suppliers': suppliers.ids,
            'categories': self.category_ids.ids,
            'products': self.product_ids.ids,
        })
        self = self.with_context(ctx)
        action = self.env['stock.warehouse.orderpoint']._get_orderpoint_action()
        return action

