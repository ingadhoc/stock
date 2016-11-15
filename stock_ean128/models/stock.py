# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    @api.one
    @api.depends('name', 'product_id', 'product_id.default_code')
    def action_compute(self):
        name = ''
        if self.product_id.default_code:
            name += ' 01 ' + self.product_id.default_code
        name += ' 10 ' + self.name
        # if self.life_date:
        #     life_date = fields.Datetime.from_string(self.life_date)
        #     name += ' 17 ' + life_date.strftime('%d%m%y')
        # else:
        #     name += ' 17 ' + 'N.A'
        self.ean_128 = name

    ean_128 = fields.Char(
        string="EAN128", compute='action_compute', store=True)

    @api.model
    def name_search(
            self, name, args=None, operator='ilike', limit=100):
        ids = []
        args = args or []
        if name:
            recs = self.search(
                args + [('ean_128', operator, name)], limit=limit)
            if ids:
                return recs.name_get()
        return super(StockProductionLot, self).name_search(
            name=name, args=args, operator=operator, limit=limit)
