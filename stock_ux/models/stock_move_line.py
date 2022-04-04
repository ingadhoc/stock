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
            product_uom_qty_location = rec.qty_done
            if rec.location_id in locations:
                # if location is source and destiny, then 0
                product_uom_qty_location = 0.0 if \
                    rec.location_dest_id in locations else -rec.qty_done
            rec.product_uom_qty_location = product_uom_qty_location

    @api.constrains('qty_done')
    def _check_manual_lines(self):
        if self._context.get('put_in_pack', False):
            return
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
        if self._context.get('put_in_pack', False):
            return
        self.mapped('move_id')._check_quantity()
        # We verify the case that does not have 'move_id' to restrict how does_check_quantity() in moves
        if any(self.filtered(lambda x: not x.move_id and x.picking_id.picking_type_id.block_additional_quantity)):
            raise ValidationError(
                _('You can not transfer more than the initial demand!'))

    @api.model
    def create(self, values):
        """ This is to solve a bug when create the sml (the value is not completed after creation)
         and should be reported to odoo to solve."""
        res = super().create(values)
        if res.picking_id and not res.description_picking:
            product = res.product_id.with_context(lang=res.picking_id.partner_id.lang or res.env.user.lang)
            res.description_picking = product._get_description(res.picking_id.picking_type_id)
        return res

    def _get_aggregated_product_quantities(self, **kwargs):
        aggregated_move_lines = super()._get_aggregated_product_quantities(**kwargs)
        if bool(self.env['ir.config_parameter'].sudo().get_param('stock_ux.delivery_slip_use_origin', 'False')) == True:
            for line in aggregated_move_lines:
                moves = self.filtered(lambda sml: sml.product_id == aggregated_move_lines[line]['product']).mapped('move_id')
                aggregated_move_lines[line]['name'] =', '.join(moves.mapped('name'))
        return aggregated_move_lines
