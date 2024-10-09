##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models, fields, api
from odoo.osv import expression


class StockWarehouseOrderpoint(models.Model):
    _name = 'stock.warehouse.orderpoint'
    _inherit = ['stock.warehouse.orderpoint', 'mail.thread']

    active_product = fields.Boolean(
        string="Product Active", related='product_id.active')
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
    reviewed = fields.Boolean()

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

    def write(self, vals):
        """ When archive a replenishment rule
        set min, max and multiple quantities in 0.
        """
        if 'active' in vals and not vals['active']:
            self.write({
                'product_min_qty': 0.0,
                'product_max_qty': 0.0,
                'qty_multiple': 0.0,
            })
        return super().write(vals)

    def _get_orderpoint_action(self):
        action = super()._get_orderpoint_action()
        action['context'] = {
            **action['context'],
            'active_test': False,
        }
        action['domain'] = expression.AND([
            action.get('domain', '[]'),
            [('active_product', '=', True)],
        ])
        return action

    def _change_review_toggle_negative(self):
        self.reviewed = False

    @api.onchange('qty_to_order')
    def _change_review_toggle_positive(self):
        self.reviewed = True

    def action_replenish(self, force_to_max=False):
        # deactivate toggle after ordering
        self._change_review_toggle_negative()
        return super(
            StockWarehouseOrderpoint, self).action_replenish(force_to_max)
