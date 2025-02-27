##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    state_detail_id = fields.Many2one(
        "stock.picking.state_detail",
        string="State Detail",
        tracking=True,
        index=True,
        copy=False,
    )

    @api.constrains("state")
    def change_state(self):
        for rec in self:
            domain = [("state", "=", rec.state), ("picking_type", "=", rec.picking_type_code)]
            state_detail = self.env["stock.picking.state_detail"].search(domain, order="sequence asc")
            if rec.state_detail_id and rec.state_detail_id in state_detail:
                continue
            rec.state_detail_id = state_detail and state_detail[0]

    @api.constrains("state_detail_id")
    def change_state_detail_id(self):
        for rec in self:
            if rec.state_detail_id:
                if (
                    rec.picking_type_id.code != rec.state_detail_id.picking_type
                    or rec.state != rec.state_detail_id.state
                ):
                    raise ValidationError(
                        f"You're selecting a state detail that doesn’t belong to this state: {rec.state} or picking type: {rec.picking_type_id.code}"
                    )
