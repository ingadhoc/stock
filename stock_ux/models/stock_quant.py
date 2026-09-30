##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    def _is_inventory_mode(self):
        """Inventory adjustments are no longer granted by being a plain
        Inventory User. The "inventory session" mode (the one that creates the
        stock.move backing an adjustment) now requires the dedicated
        ``group_stock_inventory_adjustment`` group, so an Inventory User
        without it cannot apply adjustments even if it reaches an editable
        quant view."""
        return self.env.context.get("inventory_mode") and self.env.user.has_group(
            "stock_ux.group_stock_inventory_adjustment"
        )

    @api.model
    def get_import_templates(self):
        """Ours carries the identifying column and the export/fill/re-import order, the
        core one carries neither."""
        return [
            {
                "label": _("Import Template for Inventory Adjustments"),
                "template": "/stock_ux/static/xls/stock_quant.xlsx",
            }
        ]
