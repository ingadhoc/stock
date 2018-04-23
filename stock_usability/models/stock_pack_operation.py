# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields, _
from odoo.exceptions import UserError
from odoo.addons.stock.stock import stock_pack_operation


class StockPackOperation(models.Model):

    _inherit = 'stock.pack.operation'

    used_lots = fields.Char(
        compute='_compute_used_lots'
    )

    @api.multi
    @api.depends(
        'pack_lot_ids.qty',
        'pack_lot_ids.lot_name',
    )
    def _compute_used_lots(self):
        for rec in self:
            rec.used_lots = ", ".join(rec.pack_lot_ids.mapped(
                lambda x: "%s (%s)" % (x.lot_id.display_name, x.qty)))

    @api.multi
    def set_all_done(self):
        for rec in self:
            if rec.lots_visible:
                product_qty = 0.0
                for lot in rec.pack_lot_ids:
                    lot.qty = lot.qty_todo
                    product_qty += lot.qty_todo
            else:
                product_qty = rec.product_qty
            rec.qty_done = product_qty


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
