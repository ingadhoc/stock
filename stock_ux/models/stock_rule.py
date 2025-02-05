##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class StockRule(models.Model):
    _inherit = "stock.rule"

    propagate_carrier = fields.Boolean(compute="_compute_propagate_carrier", store=True, readonly=False)

    @api.depends("picking_type_id.code")
    def _compute_propagate_carrier(self):
        """Make True by default if picking code is outgoing"""
        for rec in self:
            rec.propagate_carrier = rec.picking_type_id.code == "outgoing"
