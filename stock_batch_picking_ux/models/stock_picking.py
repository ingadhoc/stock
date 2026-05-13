from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    # Related to drive conditional logic in inherited views/modules: a batch
    # with a partner manages delivery guides at the batch level (consolidated);
    # a batch without a partner manages them per picking (individual).
    batch_partner_id = fields.Many2one(
        related="batch_id.partner_id",
        store=True,
    )

    @api.constrains("picking_type_id", "batch_id")
    def _check_picking_type_batch(self):
        for rec in self.filtered("batch_id"):
            if rec.batch_id.picking_type_id and rec.picking_type_id != rec.batch_id.picking_type_id:
                raise ValidationError(
                    _("You cannot change the operation type of a picking if it is already assigned to a batch.")
                )
