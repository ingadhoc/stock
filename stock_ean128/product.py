# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api, fields


class product_template(models.Model):
    _inherit = 'product.template'

    lot_ids = fields.One2many(
        'stock.production.lot',
        compute='get_lots',
        search='search_lots',
        string='Lots'
    )

    @api.one
    def get_lots(self):
        return self.env['stock.production.lot'].search(
            [('product_id.product_tmpl_id', '=', self.id)])

    @api.model
    def search_lots(self, operator, operand):
        if operand[0].encode('utf8') == ' ':
            operand = operand[1:]
        templates = self.env['stock.production.lot'].search(
            [('ean_128', operator, operand)]).mapped(
                'product_id').mapped('product_tmpl_id')
        return [('id', 'in', templates.ids)]


class product_product(models.Model):
    _inherit = 'product.product'

    @api.model
    def name_search(
            self, name, args=None, operator='ilike',
            limit=100):
        res = super(product_product, self).name_search(
            name, args=args, operator=operator, limit=limit)
        if len(res) < limit:
            # do not search for lots of products that are already displayed
            actual_product_ids = [x[0] for x in res]
            if name and name[0].encode('utf8') == ' ':
                name = name[1:]
            products = self.env['stock.production.lot'].search([
                ('ean_128', operator, name),
                ('product_id', 'not in', actual_product_ids),
                ],
                limit=limit).mapped('product_id')
            res += products.name_get()
        return res
