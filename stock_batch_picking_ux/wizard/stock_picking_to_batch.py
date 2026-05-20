# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockPickingToBatch(models.TransientModel):
    _inherit = "stock.picking.to.batch"

    def attach_pickings(self):
        existing_batch = self.batch_id if self.mode == "existing" else self.env["stock.picking.batch"]
        existing_partner = existing_batch.partner_id
        super().attach_pickings()
        if self.mode == "existing":
            existing_batch.partner_id = existing_partner
            return
        pickings = self.env["stock.picking"].browse(self.env.context.get("active_ids"))
        partner_id = pickings[0].partner_id if pickings else None
        all_same_partner = all(picking.partner_id == partner_id for picking in pickings)
        if all_same_partner:
            batch = pickings.batch_id
            batch.partner_id = partner_id
