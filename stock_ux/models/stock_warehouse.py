##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models
from odoo.tools.mail import plaintext2html


class StockWarehouse(models.Model):
    _name = "stock.warehouse"
    _inherit = ["stock.warehouse", "mail.thread"]

    name = fields.Char(tracking=True)
    active = fields.Boolean(tracking=True)
    code = fields.Char(tracking=True)
    reception_steps = fields.Selection(tracking=True)
    delivery_steps = fields.Selection(tracking=True)
    resupply_wh_ids = fields.Many2many(tracking=True)

    # los pasos de recepción y entrega reescriben reglas sin decir nada: es el
    # cambio de configuración que más soporte genera después
    STEP_FIELDS = ("reception_steps", "delivery_steps")

    def write(self, vals):
        if not self.env["stock.route"]._is_route_tracking_enabled():
            return super(StockWarehouse, self.with_context(tracking_disable=True)).write(vals)

        if not set(self.STEP_FIELDS) & set(vals):
            return super().write(vals)

        before = {rec.id: rec._get_rules_active_state() for rec in self}
        res = super().write(vals)
        for rec in self:
            rec._log_rules_impact(before.get(rec.id, {}))
        return res

    def _get_rules_active_state(self):
        """Estado activo/archivado de las reglas del almacén, por id."""
        self.ensure_one()
        rules = self.env["stock.rule"].sudo().with_context(active_test=False).search([("warehouse_id", "=", self.id)])
        return {rule.id: rule.active for rule in rules}

    def _log_rules_impact(self, before):
        """Deja en el chatter qué reglas quedaron activas y cuáles archivadas."""
        self.ensure_one()
        after = self._get_rules_active_state()
        Rule = self.env["stock.rule"].sudo().with_context(active_test=False)
        activated = Rule.browse([rid for rid, active in after.items() if active and not before.get(rid, False)])
        archived = Rule.browse([rid for rid, active in after.items() if not active and before.get(rid, False)])
        created = Rule.browse([rid for rid in after if rid not in before])
        if not (activated or archived or created):
            return
        lines = [self.env._("The warehouse steps changed and the rules were rewritten:")]
        for label, rules in (
            (self.env._("Activated rules"), activated - created),
            (self.env._("Archived rules"), archived),
            (self.env._("New rules"), created),
        ):
            if rules:
                lines.append("%s: %s" % (label, ", ".join(rules.mapped("display_name"))))
        self.message_post(body=plaintext2html("\n".join(lines)), subtype_xmlid="mail.mt_note")
