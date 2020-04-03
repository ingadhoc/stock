##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models, fields, api


class StockWarehouseOrderpoint(models.Model):
    _name = 'stock.warehouse.orderpoint'
    _inherit = ['stock.warehouse.orderpoint', 'mail.thread']

    rotation_stdev = fields.Float(
        compute='_compute_rotation',
        help="Desvío estandar de las cantidades entregas a clientes en los "
        "últimos 120 días.",
        digits='Product Unit of Measure',
    )
    warehouse_rotation_stdev = fields.Float(
        compute='_compute_rotation',
        help="Desvío estandar de las cantidades entregas desde este almacen"
        " a clientes en los últimos 120 días.",
        digits='Product Unit of Measure',
    )
    rotation = fields.Float(
        help='Cantidades entregadas a clientes en los '
        'últimos 120 días dividido por 4 para mensualizar '
        '(restadas devoluciones).',
        compute='_compute_rotation',
        digits='Product Unit of Measure',
    )
    warehouse_rotation = fields.Float(
        help='Cantidades entregadas desde este almacen a clientes en los '
        'últimos 120 días dividido por 4 para mensualizar'
        '(restadas devoluciones).',
        compute='_compute_rotation',
        digits='Product Unit of Measure',
    )
    product_min_qty = fields.Float(tracking=True)
    product_max_qty = fields.Float(tracking=True)
    qty_multiple = fields.Float(tracking=True)
    location_id = fields.Many2one(tracking=True)
    product_id = fields.Many2one(tracking=True)

    @api.depends('product_id', 'location_id')
    def _compute_rotation(self):
        warehouse_with_products = self.filtered('product_id')
        (self - warehouse_with_products).update({
            'rotation': 0.0,
            'rotation_stdev': 0.0,
            'warehouse_rotation_stdev': 0.0,
            'warehouse_rotation': 0.0,
        })
        for rec in warehouse_with_products:
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
