from odoo import models, fields, api


class StockWarehouseOrderpoint(models.Model):
    """ Defines Minimum stock rules. """
    _inherit = "stock.warehouse.orderpoint"

    """ add store = True for recompute fields from wizard. Only recompute by wizard """
    rotation_stdev = fields.Float(store=True)

    warehouse_rotation_stdev = fields.Float(store=True)

    rotation = fields.Float(store=True)

    warehouse_rotation = fields.Float(store=True)

    qty_forecast_stored = fields.Float(
        string="Previsión",
    )


    def update_qty_forecast(self):
        for rec in self:
            rec.qty_forecast_stored = rec.qty_forecast

    def _get_orderpoint_products(self):
        domain = [('type', '=', 'product'), ('stock_move_ids', '!=', False)]

        # Filter by suppliers
        suppliers_ids = self._context.get('filter_suppliers')
        if suppliers_ids:
            domain.append(('seller_ids.partner_id', 'in', suppliers_ids))

        # Filter by product categories
        category_ids = self._context.get('filter_categories')
        if category_ids:
            domain.append(('categ_id', 'in', category_ids))

        # Filter by products
        product_ids = self._context.get('filter_products')
        if product_ids:
            domain.append(('id', 'in', product_ids))

        return self.env['product.product'].search(domain)

    def _get_orderpoint_locations(self):
        domain = [('replenish_location', '=', True)]
        # Filter by locations
        location_ids = self._context.get('filter_locations')
        if location_ids:
            domain.append(('id', 'in', location_ids))
        return self.env['stock.location'].search(domain)
