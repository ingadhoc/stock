##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def _is_potential_existing_wave_extra(self, wave):
        # Skip waves already holding a picking its sanity check would reject: auto-waving into them would raise it.
        allowed_states = (
            ("draft", "waiting", "confirmed", "assigned")
            if wave.state == "draft"
            else ("waiting", "confirmed", "assigned")
        )
        if any(
            picking.state not in allowed_states
            or picking.company_id != wave.company_id
            or (wave.picking_type_id and picking.picking_type_id != wave.picking_type_id)
            for picking in wave.picking_ids
        ):
            return False
        return super()._is_potential_existing_wave_extra(wave)
