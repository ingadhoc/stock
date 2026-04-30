##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class PurchaseBillLineMatch(models.Model):
    _inherit = "purchase.bill.line.match"

    vouchers = fields.Char(
        string="Remitos",
        compute="_compute_vouchers",
    )

    @api.depends("pol_id.move_ids.picking_id.voucher_ids")
    def _compute_vouchers(self):
        for rec in self:
            if rec.pol_id:
                pickings = rec.pol_id.move_ids.mapped("picking_id")
                names = pickings.mapped("voucher_ids.display_name")
                rec.vouchers = ", ".join(names) if names else False
            else:
                rec.vouchers = False
