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
    name = fields.Char(
        related="move_id.name",
        related_sudo=False,
    )
    origin_description = fields.Char(
        related="move_id.origin_description",
    )

    @api.depends_context('location')
    def _compute_product_uom_qty_location(self):
        location = self._context.get('location')
        if not location:
            self.update({'product_uom_qty_location': 0.0})
            return False
        # because now we use location_id to select location, we have compelte
        # location name. If y need we can use some code of
        # _get_domain_locations on stock/product.py
        location_name = location[0]
        if isinstance(location[0], int):
            location_name = self.env['stock.location'].browse(location[0]).name
        locations = self.env['stock.location'].search([('complete_name', 'ilike', location_name)])
        for rec in self:
            product_uom_qty_location = rec.quantity
            if rec.location_id in locations:
                # if location is source and destiny, then 0
                product_uom_qty_location = 0.0 if \
                    rec.location_dest_id in locations else -rec.quantity
            rec.product_uom_qty_location = product_uom_qty_location

    @api.constrains('quantity')
    def _check_manual_lines(self):
        if self._context.get('put_in_pack', False):
            return
        if any(self.filtered(
                lambda x:
                not x.location_id.should_bypass_reservation() and
                x.picking_id.picking_type_id.block_manual_lines and
                x.reserved_qty < x.quantity)):
            raise ValidationError(_(
                "You can't transfer more quantity than reserved one!"))

    @api.constrains('quantity')
    def _check_quantity(self):
        """If we work on move lines we want to ensure quantities are ok"""
        if self._context.get('put_in_pack', False):
            return
        self.mapped('move_id')._check_quantity()
        # We verify the case that does not have 'move_id' to restrict how does_check_quantity() in moves
        if any(self.filtered(lambda x: not x.move_id and x.picking_id.picking_type_id.block_additional_quantity)):
            raise ValidationError(
                _('You can not transfer more than the initial demand!'))

    @api.model_create_multi
    def create(self, vals_list):
        """ This is to solve a bug when create the sml (the value is not completed after creation)
         and should be reported to odoo to solve."""
        recs = super().create(vals_list)
        for rec in recs:
            if rec.picking_id and not rec.description_picking:
                product = rec.product_id.with_context(lang=rec.picking_id.partner_id.lang or rec.env.user.lang)
                rec.description_picking = product._get_description(rec.picking_id.picking_type_id)
        return recs

    def _get_aggregated_product_quantities(self, **kwargs):
        aggregated_move_lines = super()._get_aggregated_product_quantities(**kwargs)
        use_origin = self.env['ir.config_parameter'].sudo().get_param('stock_ux.delivery_slip_use_origin', 'False') == 'True'
        if use_origin:
            for line in aggregated_move_lines:
                moves = self.filtered(
                    lambda sml: sml.product_id == aggregated_move_lines[line]['product']
                ).mapped('move_id').filtered(lambda m: m.origin_description)
                if moves:
                    aggregated_move_lines[line]['description'] = False
                    aggregated_move_lines[line]['name'] = ', '.join(moves.mapped('origin_description'))
        
        return aggregated_move_lines

