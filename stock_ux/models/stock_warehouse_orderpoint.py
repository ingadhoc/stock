##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp
# from odoo.tools import float_compare, float_is_zero
# from odoo.exceptions import UserError
import logging

logger = logging.getLogger(__name__)


class StockWarehouseOrderpoint(models.Model):
    _name = 'stock.warehouse.orderpoint'
    _inherit = ['stock.warehouse.orderpoint', 'mail.thread']

    rotation = fields.Float(
        help='Cantidades entregadas a clientes en los '
        'últimos 90 días dividido por 3 para mensualizar '
        '(restadas devoluciones).',
        compute='_compute_rotation',
        digits=dp.get_precision('Product Unit of Measure'),
    )
    location_rotation = fields.Float(
        help='Cantidades entregadas desde esta ubicación a clientes en los '
        'últimos 90 días dividido por 3 para mensualizar'
        '(restadas devoluciones).',
        compute='_compute_rotation',
        digits=dp.get_precision('Product Unit of Measure'),
    )
    product_min_qty = fields.Float(track_visibility='always')
    product_max_qty = fields.Float(track_visibility='always')
    qty_multiple = fields.Float(track_visibility='always')
    location_id = fields.Many2one(track_visibility='always')
    product_id = fields.Many2one(track_visibility='always')

    @api.depends('product_id', 'location_id')
    def _compute_rotation(self):
        for rec in self.filtered('product_id'):
            rec.update({
                'rotation': rec.product_id.get_product_rotation(),
                'location_rotation': rec.product_id.get_product_rotation(
                    rec.location_id)
            })
