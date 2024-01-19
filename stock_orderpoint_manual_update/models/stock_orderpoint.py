from odoo import models, fields, api


class StockWarehouseOrderpoint(models.Model):
    """ Defines Minimum stock rules. """
    _inherit = "stock.warehouse.orderpoint"

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



class StockLocation(models.Model):
    _inherit = "stock.location"

    # Heredamos método search para filtrar las ubicaciones que se usan en _get_orderpoint_action().
    # TODO: mejorar si Odoo mezcla PR: https://github.com/odoo/odoo/pull/150256
    @api.model
    def search(self, domain, offset=0, limit=None, order=None, count=False):
        location_ids = self._context.get('filter_locations')
        if location_ids:
            domain.append(('id', 'in', location_ids))
        return super().search(domain, offset=offset, limit=limit, order=order, count=count)
