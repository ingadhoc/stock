from odoo import fields, models
from odoo.fields import Domain
from odoo.tools import split_every


class StockWarehouseOrderpoint(models.Model):
    """Defines Minimum stock rules."""

    _inherit = "stock.warehouse.orderpoint"

    """ add store = True for recompute fields from wizard. Only recompute by wizard """
    rotation_stdev = fields.Float(store=True)

    warehouse_rotation_stdev = fields.Float(store=True)

    rotation = fields.Float(store=True)

    warehouse_rotation = fields.Float(store=True)

    qty_forecast_stored = fields.Float(
        string="Stored Forecast",
        digits="Product Unit",
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

        products = self.env["product.product"].search(domain)
        # mrp leaves kits out in its own override, which this one replaces without calling super()
        if "mrp.bom" in self.env:
            non_kit_ids = []
            for batch in split_every(2000, products.ids, self.env["product.product"].browse):
                kit_ids = {kit.id for kit in self.env["mrp.bom"]._bom_find(batch, bom_type="phantom")}
                non_kit_ids.extend(product_id for product_id in batch.ids if product_id not in kit_ids)
            products = self.env["product.product"].browse(non_kit_ids)
        return products

    def _get_orderpoint_locations(self):
        domain = [("replenish_location", "=", True)]
        # Filter by locations
        location_ids = self.env.context.get("filter_locations")
        if location_ids:
            domain.append(("id", "in", location_ids))
        return self.env["stock.location"].search(domain)

    def action_replenish(self):
        result = super().action_replenish()
        action = self.with_context()._get_orderpoint_action()
        orderpoint_domain = self.with_context().env["stock.warehouse.orderpoint.wizard"].get_orderpoint_domain()
        action["domain"] = Domain.AND(
            [
                action.get("domain", "[]"),
                orderpoint_domain,
            ]
        )
        if result and result.get("tag") == "display_notification":
            result.setdefault("params", {})["next"] = action
            return result
        return action
