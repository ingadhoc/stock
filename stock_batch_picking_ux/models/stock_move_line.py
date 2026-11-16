##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    origin = fields.Char(
        related="move_id.picking_id.origin",
        # we store so we can group
        store=True,
    )

    def _is_potential_existing_wave_extra(self, wave):
        # Skip waves already holding incompatible pickings: auto-waving into them would raise the batch sanity check.
        if wave.picking_ids and not (wave.picking_ids <= wave.allowed_picking_ids):
            return False
        return super()._is_potential_existing_wave_extra(wave)
