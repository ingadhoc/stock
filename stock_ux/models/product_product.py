##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api
import statistics


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # TODO implementar, para hacerlo tendriamos que almacenar los campos de stck valuation layer
    # secondary_currency_id = fields.Many2one(related='company_id.secondary_currency_id')
    # secondary_currency_value_svl = fields.Float(compute='_compute_seconday_currency_value_svl', compute_sudo=True)
    # secondary_currency_quantity_svl = fields.Float(compute='_compute_seconday_currency_value_svl', compute_sudo=True)
    # secondary_currency_avg_cost = fields.Monetary(string="Average Cost", compute='_compute_seconday_currency_value_svl', compute_sudo=True, currency_field='company_seconday_currency_')

    # @api.depends('secondary_currency_id', 'secondary_currency_value_svl', 'secondary_currency_quantity_svl', 'secondary_currency_avg_cost')
    # @api.depends_context('to_date', 'company')
    # def _compute_value_svl(self):
    #     """Compute totals of multiple svl related values"""
    #     company_id = self.env.company
    #     self.company_currency_id = company_id.currency_id
    #     domain = [
    #         ('product_id', 'in', self.ids),
    #         ('company_id', '=', company_id.id),
    #     ]
    #     if self.env.context.get('to_date'):
    #         to_date = fields.Datetime.to_datetime(self.env.context['to_date'])
    #         domain.append(('create_date', '<=', to_date))
    #     groups = self.env['stock.valuation.layer']._read_group(domain, ['value:sum', 'quantity:sum'], ['product_id'])
    #     products = self.browse()
    #     # Browse all products and compute products' quantities_dict in batch.
    #     self.env['product.product'].browse([group['product_id'][0] for group in groups]).sudo(False).mapped('qty_available')
    #     for group in groups:
    #         product = self.browse(group['product_id'][0])
    #         value_svl = company_id.currency_id.round(group['value'])
    #         avg_cost = value_svl / group['quantity'] if group['quantity'] else 0
    #         product.value_svl = value_svl
    #         product.quantity_svl = group['quantity']
    #         product.avg_cost = avg_cost
    #         product.total_value = avg_cost * product.sudo(False).qty_available
    #         products |= product
    #     remaining = (self - products)
    #     remaining.value_svl = 0
    #     remaining.quantity_svl = 0
    #     remaining.avg_cost = 0
    #     remaining.total_value = 0

    def get_product_rotation(self, location=False, compute_stdev=False):
        self.ensure_one()
        # we should use cache for this date
        from_date = fields.Datetime.subtract(
            fields.Datetime.now(self), days=120)
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

        quantities = self.env['stock.move'].search(base_domain_send).mapped(
            'product_qty') + self.env['stock.move'].search(
                base_domain_return).mapped(lambda x: -x.product_qty)
        rotation = sum(quantities) / 4.0
        if compute_stdev:
            stdev = len(quantities) > 1 and statistics.stdev(quantities) or 0.0
            return rotation, stdev
        return rotation

    def action_view_stock_move(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id('stock.stock_move_action')
        action['domain'] = [('product_id', '=', self.id)]
        action['context'] = {
            'search_default_product_id': self.id,
            'default_product_id': self.id,
        }
        return action
