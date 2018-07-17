##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockOperationWizard(models.TransientModel):

    _name = "stock.operation.wizard"

    @api.model
    def default_picking_id(self):
        picking = self.env['stock.move.line'].browse(
            self._context.get('active_ids', [])).mapped('picking_id')
        if len(picking) != 1:
            raise UserError(_(
                'Change location must be called from operations of same '
                'picking!'))
        return picking.id

    location_id = fields.Many2one(
        'stock.location',
        'Source Location',
        required=True,
    )
    location_dest_id = fields.Many2one(
        'stock.location',
        'Destination Location',
        required=True,
    )
    picking_source_location_id = fields.Many2one(
        'stock.location',
        related='picking_id.location_id',
        readonly=True,
    )
    picking_destination_location_id = fields.Many2one(
        'stock.location',
        related='picking_id.location_dest_id',
        readonly=True,
    )
    picking_id = fields.Many2one(
        'stock.picking',
        default=lambda self: self.default_picking_id(),
    )

    @api.multi
    def action_change_location(self):
        move_lines = self.env['stock.move.line'].browse(
            self._context.get('active_ids', []))
        if move_lines:
            move_lines.update({
                'location_id': self.location_id.id,
                'location_dest_id': self.location_dest_id.id
            })
