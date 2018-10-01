##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class StockMoveLine(models.Model):

    _inherit = 'stock.move.line'

    picking_create_user_id = fields.Many2one(
        'res.users',
        related='move_id.picking_create_user_id',
        string="Picking Creator",
        readonly=True,
    )

    picking_partner_id = fields.Many2one(
        'res.partner',
        'Transfer Destination Address',
        related='move_id.picking_partner_id',
        readonly=True,
    )

    picking_code = fields.Selection(
        related='move_id.picking_code',
        readonly=True,
    )

    block_additional_quantiy = fields.Boolean(
        related='picking_id.block_additional_quantiy',
        readonly=True,
    )

    product_uom_qty_location = fields.Float(
        compute='_compute_product_uom_qty_location',
        string='Net Quantity',
    )

    @api.multi
    def set_all_done(self):
        for rec in self:
            rec.update({'qty_done': rec.move_id.product_uom_qty})
        if self._context.get('from_popup', False):
            return self[0].move_id.action_show_details()

    @api.constrains('qty_done')
    def _check_quantity(self):
        for pack in self.filtered(
                lambda x: x.picking_id.block_additional_quantiy
                and x.product_qty < x.qty_done):
            raise ValidationError(_(
                'You can not transfer a product without a move on the '
                'picking!'))

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
