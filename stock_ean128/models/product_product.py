##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        res = super().name_search(
            name, args=args, operator=operator, limit=limit)
        if not limit or len(res) < limit:
            # do not search for lots of products that are already displayed
            actual_product_ids = [x[0] for x in res]
            if not args:
                args = []
            if name and name[0].encode('utf8') == ' ':
                name = name[1:]
            products = self.env['stock.production.lot'].search([
                ('ean_128', operator, name),
                ('product_id', 'not in', actual_product_ids),
            ], limit=limit).mapped('product_id')
            if products:
                prods = self.search([('id', 'in', products.ids)] + args, limit=limit)
                res += prods.name_get()
        return res
