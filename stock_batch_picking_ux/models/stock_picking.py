from odoo import _, api, models
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.constrains("picking_type_id", "batch_id")
    def _check_picking_type_batch(self):
        for rec in self.filtered("batch_id"):
            if rec.batch_id.picking_type_id and rec.picking_type_id != rec.batch_id.picking_type_id:
                raise ValidationError(
                    _("You cannot change the operation type of a picking if it is already assigned to a batch.")
                )
