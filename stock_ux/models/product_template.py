##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

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

    def action_archive(self):
        variants = self.filtered("active").product_variant_ids
        warning = variants._get_archive_stock_warning()
        res = super().action_archive()
        return variants._archive_warning_action(warning, res)
