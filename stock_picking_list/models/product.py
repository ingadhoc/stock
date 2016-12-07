# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api


class Product(models.Model):

    _inherit = 'product.product'

    @api.model
    def _get_stock(self, loc_id, type):
        res = self.with_context({'location': loc_id})._product_available()
        if type == 'virtual_available':
            return res.get(self.id).get('virtual_available')
        elif type == 'incoming_qty':
            return res.get(self.id).get('incoming_qty')
