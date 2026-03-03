##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class StockPickingVoucher(models.Model):
    _inherit = "stock.picking.voucher"

    batch_id = fields.Many2one(
        "stock.picking.batch",
        "Batch",
        ondelete="cascade",
        index=True,
    )

    picking_id = fields.Many2one(
        "stock.picking",
        "Picking",
        ondelete="cascade",
        required=False,
        index=True,
    )

    company_id = fields.Many2one(
        "res.company",
        "Company",
        related=False,
        compute="_compute_company_id",
    )

    @api.depends("picking_id.company_id", "batch_id.company_id")
    def _compute_company_id(self):
        for rec in self:
            if rec.picking_id:
                rec.company_id = rec.picking_id.company_id
            elif rec.batch_id:
                rec.company_id = rec.batch_id.company_id
            else:
                rec.company_id = False

    @api.constrains("picking_id", "batch_id")
    def _check_picking_id_required(self):
        for record in self:
            if not record.batch_id and not record.picking_id:
                raise ValidationError(
                    "Al crear un voucher debe estar ligado a una trasnferencia o lote de transferencias"
                )
