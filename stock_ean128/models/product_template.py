##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    lot_ids = fields.One2many(
        'stock.production.lot',
        compute='_compute_get_lots',
        search='_search_lots',
        string='Lots',
    )

    def _compute_get_lots(self):
        for rec in self:
            rec.lot_ids = self.env['stock.production.lot'].search(
                [('product_id.product_tmpl_id', '=', self.id)])

    @api.model
    def _search_lots(self, operator, operand):
        if operand[0].encode('utf8') == ' ':
            operand = operand[1:]
        templates = self.env['stock.production.lot'].search(
            [('ean_128', operator, operand)]).mapped(
                'product_id').mapped('product_tmpl_id')
        return [('id', 'in', templates.ids)]
