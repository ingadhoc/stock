##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp
import logging

logger = logging.getLogger(__name__)


class StockWarehouseOrderpoint(models.Model):
    _name = 'stock.warehouse.orderpoint'
    _inherit = ['stock.warehouse.orderpoint', 'mail.thread']

    rotation_stdev = fields.Float(
        compute='_compute_rotation',
        help="Desvío estandar de las cantidades entregas a clientes en los "
        "últimos 120 días.",
        digits=dp.get_precision('Product Unit of Measure'),
    )
    warehouse_rotation_stdev = fields.Float(
        compute='_compute_rotation',
        help="Desvío estandar de las cantidades entregas desde este almacen"
        " a clientes en los últimos 120 días.",
        digits=dp.get_precision('Product Unit of Measure'),
    )
    rotation = fields.Float(
        help='Cantidades entregadas a clientes en los '
        'últimos 120 días dividido por 4 para mensualizar '
        '(restadas devoluciones).',
        compute='_compute_rotation',
        digits=dp.get_precision('Product Unit of Measure'),
    )
    warehouse_rotation = fields.Float(
        help='Cantidades entregadas desde este almacen a clientes en los '
        'últimos 120 días dividido por 4 para mensualizar'
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
            rotation, rotation_stdev = rec.product_id.get_product_rotation(
                compute_stdev=True)
            warehouse_rotation, warehouse_rotation_stdev = \
                rec.product_id.get_product_rotation(
                    rec.warehouse_id.view_location_id, compute_stdev=True)
            rec.update({
                'rotation': rotation,
                'rotation_stdev': rotation_stdev,
                'warehouse_rotation_stdev': warehouse_rotation_stdev,
                'warehouse_rotation': warehouse_rotation,
            })
