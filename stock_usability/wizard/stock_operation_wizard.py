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
        picking = self.env['stock.pack.operation'].browse(
            self._context.get('active_ids', [])).mapped('picking_id')
        if len(picking) != 1:
            raise UserError(_(
                'Change location must be called from operations of same '
                'picking!'))
        return picking.id

    location_id = fields.Many2one(
        'stock.location',
        'Source Location',
        required=True
    )
    location_dest_id = fields.Many2one(
        'stock.location',
        'Destination Location',
        required=True
    )
    picking_source_location_id = fields.Many2one(
        'stock.location',
        related='picking_id.location_id'
    )
    picking_destination_location_id = fields.Many2one(
        'stock.location',
        related='picking_id.location_dest_id'
    )
    picking_id = fields.Many2one(
        'stock.picking',
        default=default_picking_id
    )

    @api.multi
    def action_change_location(self):
        pack_operations = self.env['stock.pack.operation'].browse(
            self._context.get('active_ids', []))
        if pack_operations:
            pack_operations.write({
                'location_id': self.location_id.id,
                'location_dest_id': self.location_dest_id.id
            })
