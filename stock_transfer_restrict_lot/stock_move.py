from openerp import models, fields, api, _
from openerp.exceptions import Warning


class stock_transfer_details(models.TransientModel):

    _inherit = 'stock.transfer_details'

    code = fields.Selection(
        related='picking_id.picking_type_id.code',
        string='Operation Type',
        readonly=True,)

    @api.one
    def do_detailed_transfer(self):
        items = self.item_ids.filtered(lambda r: r.lot_id)
        if self.code != 'incoming' and items:
            item_lines = items.read_group(
                [('id', 'in', items.ids)],
                ['lot_id', 'quantity'], ['lot_id'])
            for item in item_lines:
                lot = self.env['stock.production.lot'].browse(
                    item['lot_id'][0])
                if lot:
                    quants = self.env['stock.quant'].search(
                        [('id', 'in', lot.quant_ids.ids),
                         ('location_id', '=', self.item_ids[0].sourceloc_id.id)])
                    if quants:
                        qty = sum([x.qty for x in quants])
                    else:
                        qty = 0.0
                    if qty < item['quantity']:
                        raise Warning(
                            _('Sending amount can not exceed the quantity in stock for this product in this lot. \
                            \n Product:%s \
                            \n Lot:%s \
                            \n Stock:%s') % (lot.product_id.name, lot.name, qty))

            super(stock_transfer_details, self).do_detailed_transfer()
        else:
            super(stock_transfer_details, self).do_detailed_transfer()


class stock_transfer_details_items(models.TransientModel):

    _inherit = 'stock.transfer_details_items'

    @api.one
    @api.depends('product_id')
    def _check_tracking_product(self):
        check = False
        if self.product_id.track_all and not self.destinationloc_id.usage == 'inventory':
            check = True
        elif self.product_id.track_incoming and self.sourceloc_id.usage in ('supplier', 'transit', 'inventory') and self.destinationloc_id.usage == 'internal':
            check = True
        elif self.product_id.track_outgoing and self.destinationloc_id.usage in ('customer', 'transit') and self.sourceloc_id.usage == 'internal':
            check = True
        if check:
            self.lot_required = True
        else:
            self.lot_required = False

    lot_required = fields.Boolean(compute='_check_tracking_product')
    code = fields.Selection(
        related='transfer_id.picking_id.picking_type_id.code',
        string='Operation Type',
        readonly=True,)
