##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    ean_128 = fields.Char(
        string="EAN128",
        compute='_compute_action_compute',
        store=True,
    )

    @api.depends('name', 'product_id', 'product_id.default_code')
    def _compute_action_compute(self):
        for rec in self:
            name = ''
            if rec.product_id.default_code:
                name += ' 01 ' + rec.product_id.default_code
            name += ' 10 ' + rec.name
            # if self.life_date:
            #     life_date = fields.Datetime.from_string(self.life_date)
            #     name += ' 17 ' + life_date.strftime('%d%m%y')
            # else:
            #     name += ' 17 ' + 'N.A'
            rec.ean_128 = name

    @api.model
    def name_search(
            self, name, args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            recs = self.search(
                args + [('ean_128', operator, name)], limit=limit)
            if recs:
                return recs.name_get()
        return super(StockProductionLot, self).name_search(
            name=name, args=args, operator=operator, limit=limit)
