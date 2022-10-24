##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def action_view_stock_move(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id('stock.stock_move_action')
        action['domain'] = [('product_id.product_tmpl_id', 'in', self.ids)]
        action['context'] = {
            'search_default_product_id': self.product_variant_id.id,
            'default_product_id': self.product_variant_id.id,
        }
        return action
