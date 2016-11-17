from openerp import models, fields, api, _
from openerp.exceptions import UserError


class StockPackOperation(models.Model):

    _inherit = 'stock.pack.operation'

    code = fields.Selection(
        related='picking_id.picking_type_id.code',
        string='Operation Type',
        readonly=True)

    @api.one
    @api.constrains('pack_lot_ids')
    def validate_quantity(self):
        if self.code != 'incoming' and self.pack_lot_ids:
            for pack in self.pack_lot_ids:
                quants = self.env['stock.quant'].search(
                    [('id', 'in', pack.lot_id.quant_ids.ids),
                     ('location_id', '=', self.location_id.id)])
                if quants:
                    qty = sum([x.qty for x in quants])
                else:
                    qty = 0.0
                if qty < pack.qty:
                    raise UserError(
                        _('Sending amount can not exceed the quantity in\
                         stock for this product in this lot. \
                        \n Product:%s \
                        \n Lot:%s \
                        \n Stock:%s') % (pack.lot_id.product_id.
                                         name, pack.lot_id.name, qty))
