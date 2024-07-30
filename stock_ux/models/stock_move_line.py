##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import datetime
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
    
    quant_partner_id = fields.Many2one('res.partner', readonly=True, string="Creador del quant")

    def set_all_done(self):
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        for rec in self.filtered(
                lambda x: x.state not in ['draft', 'done', 'cancel']):
            rec.qty_done = rec.reserved_uom_qty \
                if not float_is_zero(
                    rec.reserved_uom_qty,
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
                x.reserved_qty < x.qty_done)):
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
        """ Returns a dictionary of products (key = id+name+description+uom) and corresponding values of interest.

        Allows aggregation of data across separate move lines for the same product. This is expected to be useful
        in things such as delivery reports. Dict key is made as a combination of values we expect to want to group
        the products by (i.e. so data is not lost). This function purposely ignores lots/SNs because these are
        expected to already be properly grouped by line.

        returns: dictionary {product_id+name+description+uom: {product, name, description, qty_done, product_uom}, ...}
        """
        aggregated_move_lines = {}

        def get_aggregated_properties(move_line=False, move=False):
            move = move or move_line.move_id
            uom = move.product_uom or move_line.product_uom_id
            name = move.product_id.display_name
            secondary_uom_qty = move.secondary_uom_qty
            secondary_uom_id = move.secondary_uom_id
            description = move.description_picking
            if description == name or description == move.product_id.name:
                description = False
            product = move.product_id
            line_key = f'{product.id}_{product.display_name}_{description or ""}_{uom.id}_{move_line.id}'
            return (line_key, name, description, uom, secondary_uom_qty, secondary_uom_id)

        # Loops to get backorders, backorders' backorders, and so and so...
        backorders = self.env['stock.picking']
        pickings = self.picking_id
        while pickings.backorder_ids:
            backorders |= pickings.backorder_ids
            pickings = pickings.backorder_ids

        for move_line in self:
            if kwargs.get('except_package') and move_line.result_package_id:
                continue
            line_key, name, description, uom, secondary_uom_qty, secondary_uom_id = get_aggregated_properties(move_line=move_line)
            qty_done = move_line.product_uom_id._compute_quantity(move_line.qty_done, uom)
            if line_key not in aggregated_move_lines:
                qty_ordered = None
                if backorders and not kwargs.get('strict'):
                    qty_ordered = move_line.move_id.product_uom_qty
                    # Filters on the aggregation key (product, description and uom) to add the
                    # quantities delayed to backorders to retrieve the original ordered qty.
                    following_move_lines = backorders.move_line_ids.filtered(
                        lambda ml: get_aggregated_properties(move=ml.move_id)[0] == line_key
                    )
                    qty_ordered += sum(following_move_lines.move_id.mapped('product_uom_qty'))
                    # Remove the done quantities of the other move lines of the stock move
                    previous_move_lines = move_line.move_id.move_line_ids.filtered(
                        lambda ml: get_aggregated_properties(move=ml.move_id)[0] == line_key and ml.id != move_line.id
                    )
                    qty_ordered -= sum(map(lambda m: m.product_uom_id._compute_quantity(m.qty_done, uom), previous_move_lines))
                aggregated_move_lines[line_key] = {'name': name,
                                                'description': description,
                                                'qty_done': qty_done,
                                                'qty_ordered': qty_ordered or qty_done,
                                                'product_uom': uom,
                                                'product': move_line.product_id,
                                                'secondary_uom_qty' : secondary_uom_qty,
                                                'secondary_uom_id' : secondary_uom_id}
            else:
                aggregated_move_lines[line_key]['qty_ordered'] += qty_done
                aggregated_move_lines[line_key]['qty_done'] += qty_done

        # Does the same for empty move line to retrieve the ordered qty. for partially done moves
        # (as they are splitted when the transfer is done and empty moves don't have move lines).
        if kwargs.get('strict'):
            return aggregated_move_lines
        pickings = (self.picking_id | backorders)
        for empty_move in pickings.move_ids:
            if not (empty_move.state == "cancel" and empty_move.product_uom_qty
                    and float_is_zero(empty_move.quantity_done, precision_rounding=empty_move.product_uom.rounding)):
                continue
            line_key, name, description, uom, secondary_uom_qty, secondary_uom_id = get_aggregated_properties(move=empty_move)

            if line_key not in aggregated_move_lines:
                qty_ordered = empty_move.product_uom_qty
                aggregated_move_lines[line_key] = {
                    'name': name,
                    'description': description,
                    'qty_done': False,
                    'qty_ordered': qty_ordered,
                    'product_uom': uom,
                    'product': empty_move.product_id,
                    'secondary_uom_qty' : secondary_uom_qty,
                    'secondary_uom_id' : secondary_uom_id,
                }
            else:
                aggregated_move_lines[line_key]['qty_ordered'] += empty_move.product_uom_qty
        return aggregated_move_lines

