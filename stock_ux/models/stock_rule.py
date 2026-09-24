##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models
from odoo.tools.mail import plaintext2html

# Campos de configuración de una regla: los que cambian a dónde y cómo se mueve
# la mercadería. Un cambio acá explica documentos raros días después.
TRACKED_FIELDS = (
    "action",
    "location_src_id",
    "location_dest_id",
    "picking_type_id",
    "procure_method",
    "route_id",
    "warehouse_id",
    "partner_address_id",
    "group_propagation_option",
    "propagate_cancel",
    "propagate_carrier",
    "auto",
    "delay",
    "sequence",
    "push_domain",
    "active",
)


class StockRule(models.Model):
    _inherit = "stock.rule"

    propagate_carrier = fields.Boolean(compute="_compute_propagate_carrier", store=True, readonly=False)

    @api.depends("picking_type_id.code")
    def _compute_propagate_carrier(self):
        """Make True by default if picking code is outgoing"""
        for rec in self:
            rec.propagate_carrier = rec.picking_type_id.code == "outgoing"

    def _log_on_route(self):
        """Las reglas se editan dentro de la ruta y su formulario suele abrirse en
        un diálogo, así que el registro de cambios vive en el chatter de la ruta."""
        if self.env.context.get("install_mode"):
            return self.env["stock.rule"]
        if not self.env["stock.route"]._is_route_tracking_enabled():
            return self.env["stock.rule"]
        return self.filtered("route_id")

    @api.model_create_multi
    def create(self, vals_list):
        rules = super().create(vals_list)
        for route, route_rules in rules._log_on_route().grouped("route_id").items():
            route.message_post(
                body=plaintext2html(self.env._("Rules added: %s", ", ".join(route_rules.mapped("display_name")))),
                subtype_xmlid="mail.mt_note",
            )
        return rules

    def write(self, vals):
        changed_fields = [name for name in vals if name in TRACKED_FIELDS]
        to_log = self._log_on_route() if changed_fields else self.env["stock.rule"]
        previous = {rule.id: {name: rule[name] for name in changed_fields} for rule in to_log}
        res = super().write(vals)
        for route, route_rules in to_log.grouped("route_id").items():
            body = route_rules._get_changes_body(previous)
            if body:
                route.message_post(body=plaintext2html(body), subtype_xmlid="mail.mt_note")
        return res

    def _get_changes_body(self, previous):
        """Texto con los cambios reales de cada regla, campo por campo."""
        Route = self.env["stock.route"]
        lines = []
        for rule in self:
            changes = []
            for name, old_value in previous.get(rule.id, {}).items():
                new_value = rule[name]
                if old_value == new_value:
                    continue
                label = self._fields[name].get_description(self.env).get("string", name)
                changes.append(
                    "%s: %s → %s"
                    % (
                        label,
                        Route._format_tracked_value("stock.rule", name, old_value),
                        Route._format_tracked_value("stock.rule", name, new_value),
                    )
                )
            if changes:
                lines.append("%s\n%s" % (self.env._("Rule %s changed:", rule.display_name), "\n".join(changes)))
        return "\n".join(lines)

    @api.ondelete(at_uninstall=False)
    def _log_deletion_on_route(self):
        for route, route_rules in self._log_on_route().grouped("route_id").items():
            route.message_post(
                body=plaintext2html(self.env._("Rules deleted: %s", ", ".join(route_rules.mapped("display_name")))),
                subtype_xmlid="mail.mt_note",
            )
