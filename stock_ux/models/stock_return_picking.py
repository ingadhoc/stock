##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class StockReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    reason = fields.Text("Reason for the return")

    def _create_return(self):
        # add to new picking for return the reason for the return
        picking = super()._create_return()
        picking.write({"note": self.reason})
        return picking
