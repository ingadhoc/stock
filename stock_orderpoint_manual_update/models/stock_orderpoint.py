from odoo import models


class StockWarehouseOrderpoint(models.Model):
    """ Defines Minimum stock rules. """
    _inherit = "stock.warehouse.orderpoint"

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
