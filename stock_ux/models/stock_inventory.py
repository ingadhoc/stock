##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, _
from odoo.exceptions import UserError


class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    def _get_inventory_lines_values(self):
        vals = super()._get_inventory_lines_values()
        if len(vals) > int(self.env["ir.config_parameter"].sudo().get_param('stock_ux.inventory_max_lines', '30000')):
            raise UserError(_('You are performing an inventory adjustment of more than 30.000 lines.'
                              ' It is recommended to make inventory adjustments in smaller batches (different subsets of products).'
                              'If you also want to modify this maximum, you can do so by creating / adjusting the system parameter stock_ux.inventory_max_lines".'
                              'Note that larger inventories may not be processed correctly due to system timeouts.'))
        return vals
