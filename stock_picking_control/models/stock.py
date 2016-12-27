# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api, fields, _
from openerp.exceptions import UserError


class StockPackOperation(models.Model):

    _inherit = 'stock.pack.operation'

    block_additional_quantiy = fields.Boolean(
        related='picking_id.block_additional_quantiy')

    @api.multi
    @api.constrains('qty_done')
    def _check_quantity(self):
        for pack in self:
            if pack.block_additional_quantiy and pack.\
                    product_qty < pack.qty_done:
                raise UserError(_(
                    'You can not transfer a product without a move on the '
                    'picking!'))

    @api.model
    def create(self, vals):
        op = super(StockPackOperation, self).create(vals)
        if op.fresh_record and op.picking_id.picking_type_id.block_add_lines:
            raise UserError(_('You can not add operations to this picking'))
        return op


class StockPickingType(models.Model):

    _inherit = 'stock.picking.type'

    # TODO rename field
    block_add_lines = fields.Boolean(
        string="Block Picking Edit",
        # string="Block add lines",
        # help="Restrict add lines")
        help="Restrict add lines, change parters and other fields edition on "
        "pickings of this type. This will only apply to users with group "
        "'Restrict Edit Blocked Pickings'")
    block_additional_quantiy = fields.Boolean(
        string="Block additional quantiy",
        help="Restrict additional quantity")


class StockPicking(models.Model):

    _inherit = 'stock.picking'

    block_add_lines = fields.Boolean(
        related='picking_type_id.block_add_lines')
    block_additional_quantiy = fields.Boolean(
        related='picking_type_id.block_additional_quantiy')
