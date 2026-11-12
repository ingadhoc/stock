##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    free_qty = fields.Float(search="_search_free_qty")

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

    def _search_free_qty(self, operator, value):
        variants = self.env["product.product"]._search([("free_qty", operator, value)])
        return [("product_variant_ids", "in", variants)]
