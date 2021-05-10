##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, _
import statistics


class ProductProduct(models.Model):
    _inherit = 'product.product'

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
        action = self.env.ref('stock.stock_move_action').read()[0]
        action['domain'] = [('product_id', '=', self.id)]
        action['context'] = {
            'search_default_product_id': self.id,
            'default_product_id': self.id,
        }
        return action

    def action_revaluation(self):
        self.ensure_one()
        ctx = dict(self._context, default_product_id=self.id, default_company_id=self.env.company.id)
        return {
            'name': _("Product Revaluation"),
            'view_mode': 'form',
            'res_model': 'stock.valuation.layer.revaluation',
            'view_id': self.env.ref('stock_ux.stock_valuation_layer_revaluation_form_view').id,
            'type': 'ir.actions.act_window',
            'context': ctx,
            'target': 'new'
        }
