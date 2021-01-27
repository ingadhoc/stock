##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockMassCancelRemainingWizard(models.TransientModel):
    _name = "stock.mass.cancel.remaining.wizard"
    _description = "Stock mass cancel remaining wizard"

    move_ids = fields.Many2many('stock.move', readonly=True)
    model = fields.Char()

    @api.model
    def default_get(self, fields):
        vals = super().default_get(fields)
        moves_ids = self.env.context.get('moves_ids')
        model = self.env.context.get('model')
        if model and moves_ids:
            vals['move_ids'] = [(6, 0, moves_ids)]
            vals['model'] = model
        return vals

    def action_confirm(self):
        if self.model == 'sale.order.line':
            orders = self.move_ids.mapped('sale_line_id')
        elif self.model == 'purchase.order.line':
            orders = self.move_ids.mapped('purchase_line_id')
        else:
            raise UserError("This operation it's Only for Sale/Purchase moves")
        bom_enable = 'bom_ids' in self.env['product.template']._fields
        for line in orders.filtered('product_id'):
            if bom_enable:
                bom = self.env['mrp.bom']._bom_find(
                    product=line.product_id)
                if bom.type == 'phantom':
                    raise UserError(_(
                        "Cancel remaining can't be called for Kit Products "
                        "(products with a bom of type kit)."))
            old_product_uom_qty = line.product_uom_qty
            line.with_context(
                bypass_protecion=True).product_uom_qty = line.qty_delivered
            to_cancel_moves = line.move_ids.filtered(
                lambda x: x.state not in ['done', 'cancel'])
            to_cancel_moves._cancel_quantity()
            line.order_id.message_post(
                body=_(
                    'Cancel remaining call for line "%s" (id %s), line '
                    'qty updated from %s to %s') % (
                        line.name, line.id,
                        old_product_uom_qty, line.product_uom_qty))
