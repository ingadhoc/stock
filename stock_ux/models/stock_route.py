##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models

# Single switch for routes, rules and warehouses, set from Inventory settings
ROUTE_TRACKING_PARAM = "stock_ux.route_tracking"


class StockRoute(models.Model):
    _name = "stock.route"
    _inherit = ["stock.route", "mail.thread"]

    name = fields.Char(tracking=True)
    active = fields.Boolean(tracking=True)
    sequence = fields.Integer(tracking=True)
    product_selectable = fields.Boolean(tracking=True)
    product_categ_selectable = fields.Boolean(tracking=True)
    warehouse_selectable = fields.Boolean(tracking=True)
    package_type_selectable = fields.Boolean(tracking=True)
    company_id = fields.Many2one(tracking=True)
    supplied_wh_id = fields.Many2one(tracking=True)
    supplier_wh_id = fields.Many2one(tracking=True)
    warehouse_ids = fields.Many2many(tracking=True)

    @api.model
    def _is_route_tracking_enabled(self):
        # core deletes the parameter when the setting is unchecked, so a missing one means off
        value = self.env["ir.config_parameter"].sudo().get_param(ROUTE_TRACKING_PARAM, "False")
        return str(value).strip().lower() not in ("false", "0", "")

    def write(self, vals):
        if not self._is_route_tracking_enabled():
            self = self.with_context(tracking_disable=True)
        return super(StockRoute, self).write(vals)

    @api.model
    def _format_tracked_value(self, model, field_name, value):
        """Readable value of a field, for the rule change notes."""
        field = self.env[model]._fields[field_name]
        if field.type == "many2one":
            return value.display_name if value else self.env._("(empty)")
        if field.type == "selection":
            selection = dict(self.env[model].fields_get([field_name])[field_name]["selection"])
            return selection.get(value, value) or self.env._("(empty)")
        if field.type == "boolean":
            return self.env._("Yes") if value else self.env._("No")
        if value is False or value is None or value == "":
            return self.env._("(empty)")
        return str(value)
