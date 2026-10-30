from odoo import fields, models
from odoo.fields import Domain


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
        ctx = {
            "filter_products": self.product_ids.ids,
            "filter_categories": self.category_ids.ids,
            "filter_suppliers": self.supplier_ids.ids,
            "filter_by_main_supplier": self.filter_by_main_supplier,
            "filter_locations": self.location_ids.ids,
        }
        action = self.with_context(**ctx).env["stock.warehouse.orderpoint"]._get_orderpoint_action()
        # The same domain as the list shown after ordering, so both always match
        orderpoint_domain = self.with_context(**ctx).get_orderpoint_domain()
        orderpoints = self.env["stock.warehouse.orderpoint"].with_context(active_test=False).search(orderpoint_domain)
        orderpoints.update_qty_forecast()
        if self.compute_rotation:
            orderpoints._compute_rotation()
        orderpoints._change_review_toggle_negative()
        action["domain"] = Domain.AND(
            [
                action.get("domain", "[]"),
                orderpoint_domain,
            ]
        )
        return action

    def get_orderpoint_domain(self):
        orderpoint_domain = []
        if self.env.context.get("filter_products", []):
            orderpoint_domain.append(("product_id", "in", self.env.context.get("filter_products", [])))
        if self.env.context.get("filter_categories", []):
            orderpoint_domain.append(("product_category_id", "in", self.env.context.get("filter_categories", [])))
        suppliers = self.env.context.get("filter_suppliers", [])
        if suppliers and self.env.context.get("filter_by_main_supplier"):
            orderpoint_domain.append(("supplier_id.partner_id", "in", suppliers))
        elif suppliers:
            orderpoint_domain.append(("product_id.seller_ids.partner_id", "in", suppliers))
        if self.env.context.get("filter_locations", []):
            orderpoint_domain.append(("location_id", "in", self.env.context.get("filter_locations", [])))
        return orderpoint_domain
