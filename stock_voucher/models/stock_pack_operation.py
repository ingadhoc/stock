##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api


class StockPicking(models.Model):
    _inherit = 'stock.pack.operation'

    @api.multi
    @api.constrains(
        # product_qty no seria necesario y ademas hace que se recompute al
        # validar el picking, cosa que no queremos por si el usuario puso
        # algun valor a mano
        # 'product_qty',
        'qty_done',
    )
    def recompute_declared_value(self):
        """
        Recompute declared value. Used when qty changes not form view
        """
        self.mapped('picking_id').product_onchange()
