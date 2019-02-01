##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare, float_is_zero


class StockMove(models.Model):
    _inherit = 'stock.move'

    used_lots = fields.Char(
        compute='_compute_used_lots',
    )
    picking_create_user_id = fields.Many2one(
        'res.users',
        related='picking_id.create_uid',
        string="Picking Creator",
        readonly=True,
    )
    picking_dest_id = fields.Many2one(
        related='move_dest_ids.picking_id',
        readonly=True,
    )
    lots_visible = fields.Boolean(
        related='move_line_ids.lots_visible',
        readonly=True,
    )

    @api.depends(
        'move_line_ids.qty_done',
        'move_line_ids.lot_id',
    )
    def _compute_used_lots(self):
        for rec in self:
            rec.used_lots = ", ".join(rec.move_line_ids.mapped(
                lambda x: "%s (%s)" % (x.lot_id.name, x.qty_done)))

    @api.multi
    def set_all_done(self):
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        for rec in self:
            rec.quantity_done = rec.reserved_availability\
                if not float_is_zero(
                    rec.reserved_availability,
                    precision_digits=precision) else\
                rec.product_uom_qty

    @api.constrains('quantity_done')
    def _check_quantity(self):
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        for rec in self.filtered(
            lambda
            x: x.picking_id.picking_type_id.
            block_additional_quantity and float_compare(
                x.product_uom_qty, x.quantity_done,
                precision_digits=precision) == -1):
            raise ValidationError(_(
                'You can not transfer more than the initial demand!'))
