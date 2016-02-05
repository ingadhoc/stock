from openerp import models, api, fields, _
from openerp.exceptions import Warning


class stock_transfer_details(models.TransientModel):

    _inherit = 'stock.transfer_details'

    block_quantity = fields.Boolean(
        related='picking_id.block_quantity')

    @api.one
    @api.constrains('item_ids')
    def _check_quantity(self):
        if self.item_ids and self.block_quantity:
            items_prod_qty = self.item_ids.read_group(
                [('id', 'in', self.item_ids.ids)],
                ['product_id', 'quantity'], ['product_id'])
            moves = self.picking_id.move_lines
            for item_prod_qty in items_prod_qty:
                item_product = item_prod_qty.get('product_id')
                item_quantity = item_prod_qty.get('quantity')
                moves_prod_qty = moves.read_group(
                    [('id', 'in', moves.ids),
                        ('product_id', '=', item_product[0])],
                    ['product_id', 'product_qty'], ['product_id'])
                if not moves_prod_qty:
                    raise Warning(_(
                        'You can not transfer a product without a move on the '
                        'picking!'))
                if item_quantity > moves_prod_qty[0].get('product_qty'):
                    raise Warning(_(
                        'Quantity to send for "%s" can not be greater than the'
                        ' remaining quantity for this move.') % (
                        item_product[1]))


class stock_move(models.Model):

    _inherit = 'stock.move'

    block_quantity = fields.Boolean(
        related='picking_id.block_quantity')


class stock_picking(models.Model):

    _inherit = 'stock.picking'

    block_quantity = fields.Boolean(compute='_get_block_quantity')

    @api.one
    @api.depends(
        'picking_type_id.code',
        'company_id.block_internal_move',
        'company_id.block_outgoing_move',
        'company_id.block_incoming_move'
    )
    def _get_block_quantity(self):
        self.block_quantity = False
        if self.company_id.block_internal_move and self.picking_type_id.code == 'internal':
            self.block_quantity = True
        elif self.company_id.block_outgoing_move and self.picking_type_id.code == 'outgoing':
            self.block_quantity = True
        elif self.company_id.block_incoming_move and self.picking_type_id.code == 'incoming':
            self.block_quantity = True
