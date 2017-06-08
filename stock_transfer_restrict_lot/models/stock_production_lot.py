# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api


class StockProductionlot(models.Model):

    _inherit = 'stock.production.lot'

    qty_available_not_res = fields.Float(
        compute='_compute_qty_available_not_res',
        string='Qty Available Not Reserved',
        store=True
    )

    @api.multi
    @api.depends('quant_ids.reservation_id', 'quant_ids.qty')
    def _compute_qty_available_not_res(self):
        for rec in self:
            rec.qty_available_not_res = sum(rec.quant_ids.filtered(
                lambda x: not x.reservation_id).mapped('qty'))

    @api.multi
    def name_get(self):
        result = []
        for rec in self:
            read = rec.quant_ids.read_group(
                [('lot_id', '=', rec.id)],
                ['location_id', 'qty'], 'location_id')
            locations_qty = ', '.join(
                ['%s: %s' % (x['location_id'][1], x['qty']) for x in read])
            name = '%s (%s)' % (rec.name, locations_qty)
            result.append((rec.id, name))
        return result
