##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
<<<<<<< 39f3d3941ec9262c736601e62267d02d5dc3b5f4:stock_request_ux/tests/__init__.py
from . import test_reassign_once
||||||| ded1fa114c1cdc2dbc5924bba06083638942b957:stock_batch_picking_ux/models/stock_move_line.py
from odoo import fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    origin = fields.Char(
        related="move_id.picking_id.origin",
        # we store so we can group
        store=True,
    )
=======
from odoo import fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    origin = fields.Char(
        related="move_id.picking_id.origin",
        # we store so we can group
        store=True,
    )

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
>>>>>>> 268e7af029baae5233a7ed1d5e1290eaf1a750e1:stock_batch_picking_ux/models/stock_move_line.py
