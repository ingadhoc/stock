# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api, _
from openerp.exceptions import ValidationError


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
