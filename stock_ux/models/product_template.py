##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    route_ids = fields.Many2many(tracking=True)

    def write(self, vals):
        # el seguimiento de rutas se puede apagar desde Ajustes de Inventario
        if "route_ids" in vals and not self.env["stock.route"]._is_route_tracking_enabled():
            self = self.with_context(tracking_disable=True)
        return super(ProductTemplate, self).write(vals)

    @api.model
    def get_import_templates(self):
        if self.env.context.get("stock_product_template"):
            return [
                {
                    "label": _("Import Template for Products"),
                    "template": "/stock_ux/static/xls/product_template.xlsx",
                }
            ]
        return super().get_import_templates()

    def action_view_stock_move(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.stock_move_action")
        action["domain"] = [("product_id.product_tmpl_id", "in", self.ids)]
        action["context"] = {
            "search_default_product_id": self.product_variant_id.id,
            "default_product_id": self.product_variant_id.id,
        }
        return action
