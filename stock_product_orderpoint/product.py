# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields


class product_product(models.Model):
    _inherit = 'product.product'

    nbr_reordering_rules = fields.Integer(
        'Reordering Rules', 
        compute='_compute_nbr_reordering_rules')

    reordering_min_qty = fields.Float(compute='_compute_nbr_reordering_rules')
    reordering_max_qty = fields.Float(compute='_compute_nbr_reordering_rules')


    def _compute_nbr_reordering_rules(self):
        read_group_res = self.env['stock.warehouse.orderpoint'].read_group(
            [('product_id', 'in', self.ids)],
            ['product_id', 'product_min_qty', 'product_max_qty'],
            ['product_id'])
        res = {i: {} for i in self.ids}
        for data in read_group_res:
            res[data['product_id'][0]]['nbr_reordering_rules'] = int(data['product_id_count'])
            res[data['product_id'][0]]['reordering_min_qty'] = data['product_min_qty']
            res[data['product_id'][0]]['reordering_max_qty'] = data['product_max_qty']
        for product in self:
            product.nbr_reordering_rules = res[product.id].get('nbr_reordering_rules', 0)
            product.reordering_min_qty = res[product.id].get('reordering_min_qty', 0)
            product.reordering_max_qty = res[product.id].get('reordering_max_qty', 0)
