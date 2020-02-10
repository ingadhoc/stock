##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError
from odoo.tools import float_is_zero


class StockMoveLine(models.Model):

    _inherit = 'stock.move.line'

    picking_create_user_id = fields.Many2one(
        'res.users',
        # vamos a traves de picking para legar mas rapido y no pasar por move
        related='picking_id.create_uid',
        string="Picking Creator",
    )
    picking_partner_id = fields.Many2one(
        'res.partner',
        'Transfer Destination Address',
        # vamos a traves de picking para legar mas rapido y no pasar por move
        related='picking_id.partner_id',
    )
    picking_code = fields.Selection(
        related='picking_type_id.code',
    )
    picking_type_id = fields.Many2one(
        related='picking_id.picking_type_id',
        store=True,
    )
    product_uom_qty_location = fields.Float(
        compute='_compute_product_uom_qty_location',
        string='Net Quantity',
    )

    @api.multi
    def set_all_done(self):
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        for rec in self.filtered(
                lambda x: x.state not in ['draft', 'done', 'cancel']):
            rec.qty_done = rec.product_uom_qty \
                if not float_is_zero(
                    rec.product_uom_qty,
                    precision_digits=precision) else \
                rec.move_id.product_uom_qty
            if self._context.get('from_popup', False):
                return self[0].move_id.action_show_details()

    @api.multi
    def _compute_product_uom_qty_location(self):
        location = self._context.get('location')
        if not location:
            return False
        # because now we use location_id to select location, we have compelte
        # location name. If y need we can use some code of
        # _get_domain_locations on stock/product.py
        locations = self.env['stock.location'].search(
            [('complete_name', 'ilike', location)])
        # from_locations = self.env['stock.location'].search([
        #     '|', ('name', 'ilike', location),
        #     ('location_dest_id', 'ilike', location)
        #     ])
        for rec in self:
            product_uom_qty_location = rec.qty_done
            if rec.location_id in locations:
                # if location is source and destiny, then 0
                product_uom_qty_location = 0.0 if \
                    rec.location_dest_id in locations else -rec.qty_done
            rec.product_uom_qty_location = product_uom_qty_location

    @api.constrains('qty_done')
    def _check_manual_lines(self):
        if any(self.filtered(
                lambda x:
                not x.location_id.should_bypass_reservation() and
                x.picking_id.picking_type_id.block_manual_lines and
                x.product_qty < x.qty_done)):
            raise ValidationError(_(
                "You can't transfer more quantity than reserved one!"))

    @api.constrains('qty_done')
    def _check_quantity(self):
        """If we work on move lines we want to ensure quantities are ok"""
        self.mapped('move_id')._check_quantity()
        # We verify the case that does not have 'move_id' to restrict how does_check_quantity() in moves
        if any(self.filtered(lambda x: not x.move_id and x.picking_id.picking_type_id.block_additional_quantity)):
            raise ValidationError(_('You can not transfer more than the initial demand!'))
