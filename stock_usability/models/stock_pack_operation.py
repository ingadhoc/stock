# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api, _
from openerp.exceptions import ValidationError, UserError
from openerp.addons.stock.stock import stock_pack_operation


class StockPackOperation(models.Model):

    _inherit = 'stock.pack.operation'

    @api.multi
    def set_all_done(self):
        for rec in self:
            if rec.lots_visible:
                raise ValidationError(_(
                    'You can not Set all Done for product "%s" because it '
                    'requires lot on operation "%s"') % (
                    rec.product_id.name,
                    rec.picking_id.picking_type_id.name))
            rec.qty_done = rec.product_qty


@api.multi
def unlink(self):
    # modificamos para que se pudan borrar las operations aun si el picking
    # esta realizado o cancelado (el campo state de las op es related al state
    # de picking)
    if not self._context.get('force_op_unlink') and any(
            [x.state in ('done', 'cancel') for x in self]):
        raise UserError(_(
            'You can not delete pack operations of a done picking'))
    return super(stock_pack_operation, self).unlink()


stock_pack_operation.unlink = unlink
