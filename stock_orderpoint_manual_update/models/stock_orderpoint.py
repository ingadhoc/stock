from odoo import models, fields


class StockWarehouseOrderpoint(models.Model):
    """ Defines Minimum stock rules. """
    _inherit = "stock.warehouse.orderpoint"

    qty_forecast_stored = fields.Float(
        string="Previsión",
    )

    def _get_orderpoint_action(self):
        action = super()._get_orderpoint_action()
        orderpoints = self.with_context(active_test=False).search([])
        for rec in orderpoints:
            rec.qty_forecast_stored = rec.qty_forecast
        return action

    def _get_orderpoint_products(self):
        domain = [('type', '=', 'product'), ('stock_move_ids', '!=', False)]

        # Filter by suppliers
        suppliers_ids = self._context.get('suppliers')
        suppliers = self.env['product.supplierinfo'].browse(suppliers_ids)
        if suppliers:
            domain += ['|', ('product_tmpl_id', 'in', suppliers.product_tmpl_id.ids), ('id', 'in', suppliers.product_id.ids)]

        # Filter by product categories
        category_ids = self._context.get('categories')
        if category_ids:
            domain += [('categ_id', 'in', category_ids)]

        # Filter by products
        product_ids = self._context.get('products')
        if product_ids:
            domain += [('id', 'in', product_ids)]

        return self.env['product.product'].search(domain)
