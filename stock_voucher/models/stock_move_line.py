##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    @api.constrains(
        'qty_done',
    )
    def recompute_declared_value(self):
        """
        Recompute declared value. Used when qty changes not form view
        """
        self.mapped('picking_id').product_onchange()
