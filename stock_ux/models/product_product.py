##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields,  api
from datetime import timedelta, datetime


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def get_product_rotation(self, location=False):
        self.ensure_one()
        # we should use cache for this date
        from_date = fields.Datetime.to_string(
            datetime.now() + timedelta(-90))
        base_domain = [
            ('date', '>=', from_date),
            ('state', '=', 'done'),
            ('product_id', '=', self.id),
        ]
        base_domain_send = base_domain + [
            ('location_dest_id.usage', '=', 'customer')]
        base_domain_return = base_domain + [
            ('location_id.usage', '=', 'customer')]

        if location:
            base_domain_send += [('location_id', 'child_of', location.id)]
            base_domain_return += [
                ('location_dest_id', 'child_of', location.id)]

        # from any location to customers
        rotation = sum(self.env['stock.move'].search(
            base_domain_send).mapped('product_qty'))
        # from customers to any location
        rotation -= sum(self.env['stock.move'].search(
            base_domain_return).mapped('product_qty'))
        return rotation / 3.0
