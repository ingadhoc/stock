##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields, _
from odoo.exceptions import UserError


class StockPackOperation(models.Model):

    _inherit = 'stock.pack.operation'

    block_additional_quantiy = fields.Boolean(
        related='picking_id.block_additional_quantiy', readonly=True,)

    @api.multi
    @api.constrains('qty_done')
    def _check_quantity(self):
        for pack in self:
            if pack.picking_id.block_additional_quantiy and pack.\
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
        "'Restrict Edit Blocked Pickings'. It also block pickings duplicate.")
    block_additional_quantiy = fields.Boolean(
        string="Block additional quantiy",
        help="Restrict additional quantity")
    block_picking_deletion = fields.Boolean(
        string="Block picking deletion",
        default=True,
        help="Do not allow to remove pickings")


class StockPicking(models.Model):

    _inherit = 'stock.picking'

    block_add_lines = fields.Boolean(
        related='picking_type_id.block_add_lines', readonly=True,)
    block_additional_quantiy = fields.Boolean(
        related='picking_type_id.block_additional_quantiy', readonly=True,)

    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        # si no viene default entonces es por interfaz y
        # si tiene bloeado agregar líneas entonces tiene bloqueado duplicar
        if not default and self.block_add_lines:
            raise UserError(_(
                'You can not duplicate a Picking because "Block Pikcking Edit"'
                ' is enable on the picking type "%s"') % (
                self.picking_type_id.name))
        return super(StockPicking, self).copy(default=default)

    @api.multi
    def unlink(self):
        """
        To avoid errors we block deletion of pickings in other state than
        draft or cancel
        """
        not_del_pickings = self.filtered(
            lambda x: x.picking_type_id.block_picking_deletion)
        if not_del_pickings:
            raise UserError(_(
                'You can not delete this pickings because "Block picking '
                'deletion" is enable on the picking type "%s".\n'
                'Picking Ids: %s') % (
                    not_del_pickings.ids, self.picking_type_id.name))
        return super(StockPicking, self).unlink()
