from odoo import fields, models
from odoo.osv import expression


class StockWarehouseOrderpointWizard(models.TransientModel):
    _name = "stock.warehouse.orderpoint.wizard"
    _description = "Stock Warehouse Orderpoint Wizard"

    company_id = fields.Many2one("res.company", "Company", default=lambda self: self.env.company)
    product_ids = fields.Many2many("product.product", string="Product")
    category_ids = fields.Many2many("product.category", string="Product Category")
    supplier_ids = fields.Many2many("res.partner", string="Vendor", check_company=True)
    filter_by_main_supplier = fields.Boolean(string="Filter by Main Vendor")
    location_ids = fields.Many2many("stock.location", string="Location")
    compute_rotation = fields.Boolean(
        help="If checked, the wizard will compute the rotation of the orderpoints. This may take some time.",
        default=False,
    )

    def action_confirm(self):
        """Generate orderpoints and apply filters to the view.

        Temporary orderpoints are created for all products that need them (standard Odoo behavior).
        Then filters are applied at the view level to show only relevant orderpoints.
        """
        ctx = {
            "filter_products": self.product_ids.ids,
            "filter_categories": self.category_ids.ids,
            "filter_suppliers": self.supplier_ids.ids,
            "filter_locations": self.location_ids.ids,
        }
        # _get_orderpoint_action() will create temporary orderpoints based on ctx filters
        action = self.with_context(**ctx).env["stock.warehouse.orderpoint"]._get_orderpoint_action()

        # Get all orderpoints that were created/found (includes temporary ones just created)
        orderpoint_domain = self._get_orderpoint_domain()
        orderpoints = self.env["stock.warehouse.orderpoint"].with_context(active_test=False).search(orderpoint_domain)

        # Update calculations for the filtered orderpoints only
        orderpoints.update_qty_forecast()
        if self.compute_rotation:
            orderpoints._compute_rotation()
        orderpoints._change_review_toggle_negative()

        # Apply the same domain to the action view
        if orderpoint_domain:
            action["domain"] = expression.AND([action.get("domain", []), orderpoint_domain])

        return action

    def _get_orderpoint_domain(self):
        """Build domain for filtering orderpoints.

        Temporary orderpoints are already filtered by product/category/location through
        _get_orderpoint_products()/_get_orderpoint_locations(), so we just need to handle
        the supplier filter specially (using OR to include temporaries without supplier).
        """
        if not any([self.product_ids, self.category_ids, self.supplier_ids, self.location_ids]):
            return []

        domain = []
        if self.product_ids:
            domain.append(("product_id", "in", self.product_ids.ids))
        if self.category_ids:
            domain.append(("product_category_id", "in", self.category_ids.ids))
        if self.location_ids:
            domain.append(("location_id", "in", self.location_ids.ids))

        # Supplier filter: use OR to include temporary orderpoints (which don't have supplier_id)
        if self.supplier_ids:
            supplier_filter = (
                ("supplier_id.partner_id", "in", self.supplier_ids.ids)
                if self.filter_by_main_supplier
                else ("product_id.seller_ids.partner_id", "in", self.supplier_ids.ids)
            )
            # (base_filters AND supplier) OR (base_filters AND trigger=auto)
            return expression.OR([domain + [supplier_filter], domain + [("trigger", "=", "auto")]])

        return domain

    def get_orderpoint_domain(self):
        """Build domain from context. Used by action_replenish to apply wizard filters."""
        ctx = self.env.context
        if not any(
            [
                ctx.get("filter_products"),
                ctx.get("filter_categories"),
                ctx.get("filter_suppliers"),
                ctx.get("filter_locations"),
            ]
        ):
            return []

        domain = []
        if ctx.get("filter_products"):
            domain.append(("product_id", "in", ctx.get("filter_products")))
        if ctx.get("filter_categories"):
            domain.append(("product_category_id", "in", ctx.get("filter_categories")))
        if ctx.get("filter_locations"):
            domain.append(("location_id", "in", ctx.get("filter_locations")))

        # Supplier filter only for permanent orderpoints
        if ctx.get("filter_suppliers"):
            supplier_domain = domain + [("supplier_id.partner_id", "in", ctx.get("filter_suppliers"))]
            return expression.OR([supplier_domain, domain + [("trigger", "=", "auto")]])

        return domain
