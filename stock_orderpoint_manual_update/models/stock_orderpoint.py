from odoo import fields, models
from odoo.fields import Domain


class StockWarehouseOrderpoint(models.Model):
    """Defines Minimum stock rules."""

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
        domain = [("is_storable", "=", True), ("stock_move_ids", "!=", False)]

        # Filter by suppliers
        suppliers_ids = self.env.context.get("filter_suppliers")
        if suppliers_ids:
            domain.append(("seller_ids.partner_id", "in", suppliers_ids))

        # Filter by product categories
        category_ids = self.env.context.get("filter_categories")
        if category_ids:
            domain.append(("categ_id", "in", category_ids))

        # Filter by products
        product_ids = self.env.context.get("filter_products")
        if product_ids:
            domain.append(("id", "in", product_ids))

        return self.env["product.product"].search(domain)

    def _get_orderpoint_locations(self):
        domain = [("replenish_location", "=", True)]
        # Filter by locations
        location_ids = self.env.context.get("filter_locations")
        if location_ids:
            domain.append(("id", "in", location_ids))
        return self.env["stock.location"].search(domain)

    def action_replenish(self):
        notification = super().action_replenish()
        # Si el super devuelve una notificación (para transferencias inter-warehouse), la devolvemos
        if notification:
            return notification
        action = self.with_context()._get_orderpoint_action()
        orderpoint_domain = self.with_context().env["stock.warehouse.orderpoint.wizard"].get_orderpoint_domain()
        action["domain"] = Domain.AND(
            [
                action.get("domain", "[]"),
                orderpoint_domain,
            ]
        )
        return action

    def update_qty_to_order_orderpoint(self):
        """
        Updates qty_to_order for orderpoints.
        In v19, qty_to_order is a computed field that depends on qty_to_order_computed (stored)
        and qty_to_order_manual. We invalidate the cache to force recalculation.
        """
        valid_orderpoints = self.exists()
        if valid_orderpoints:
            # Invalidate cache to force recalculation instead of direct compute
            # This avoids concurrency issues during scheduler execution
            valid_orderpoints.invalidate_recordset(["qty_to_order_computed", "qty_to_order"])
            # Access the field to safely trigger compute
            valid_orderpoints.mapped("qty_to_order")
