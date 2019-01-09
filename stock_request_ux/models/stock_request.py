##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class StockRequest(models.Model):
    _inherit = 'stock.request'

    picking_ids = fields.One2many(
        compute='_compute_picking_ids',
    )
    picking_count = fields.Integer(
        compute='_compute_picking_ids',
    )

    @api.onchange('product_id')
    def onchange_product_id(self):
        res = super(StockRequest, self).onchange_product_id()
        if self.order_id.route_id in self.route_ids:
            self.route_id = self.order_id.route_id.id
        return res

    @api.depends('allocation_ids')
    def _compute_picking_ids(self):
        for rec in self.filtered('procurement_group_id'):
            all_moves = self.env['stock.move'].search(
                [('group_id', '=', rec.procurement_group_id.id)]
            )
            rec.picking_ids = all_moves.mapped('picking_id')
            rec.picking_count = len(rec.picking_ids)

    def action_cancel(self):
        """ Con esto queremos cancelar todos lo moves/pickings vinculados (que
        se hayan generado por la rule). No es muy elegante buscar por producto
        pero al no estar almacenandno el link al request fue la mas facil.
        TODO: supongo que lo ideal seria:
        1) poder identificar bien las lineas, ya sea llevando el stock request
        a cada move y no solo el inicial, o obteniendo el move original y luego
        llegar a los otros por los links entre moves (movimiento de destino).
        Esto seria mas que nada para que sea mas elegante
        2) por ahora agregamos constraint para que no pueda haber dos productos
        iguales en pero en realidad habria que en vez de cancelar, hacer un
        cancel remaining solo por lo que este request representaba. No lo
        podemos hacer analogo a como se hace en ventas ya que las ventas
        mantienen distintos moves y por eso funciona bien.
        """
        # hacemos analogo a odoo en sale, cancelamos todos los moves de los
        # pickings  relacionados a cada linea

        # por ahora no filtramos por state porque en realidad si algo
        # esta entregado no queremos que lo pueda cancelar
        # self.sudo().picking_ids.mapped('move_lines').filtered(
        #     lambda x: x.state not in (
        #         'done', 'cancel') and x.product_id == self.product_id
        # )._action_cancel()
        self.sudo().picking_ids.mapped('move_lines').filtered(
            lambda x: x.product_id == self.product_id)._action_cancel()
        self.state = 'cancel'
        return True

    @api.constrains('procurement_group_id', 'product_id')
    def _check_product_stock_request(self):
        for rec in self.filtered(
                lambda x: x.procurement_group_id and x.product_id):
            domain = [
                ('product_id', '=', rec.product_id.id),
                ('procurement_group_id', '=', rec.procurement_group_id.id),
            ]
            if self.search_count(domain) > 1:
                raise ValidationError(_(
                    'You can not repeat product on procurement group!\n'
                    '* Product: %s\n'
                    '* Procurement Group: %s' % (
                        rec.product_id.name, rec.procurement_group_id.name)))
