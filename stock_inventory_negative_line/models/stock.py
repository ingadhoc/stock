# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api


class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    @api.multi
    def action_done(self):
        """ Finish the inventory
        @return: True
        """
        for inv in self:
            # for inventory_line in inv.line_ids:
            #     if inventory_line.product_qty\
            #         < 0 and inventory_line.product_qty \
            #             != inventory_line.theoretical_qty:
            #         raise osv.except_osv\
            #             (_('Warning'), _('You cannot set a negative\
            #          product quantity in an inventory line\
            #          : n\t % s - qty: % s' % (inventory_line.product_id.name,
            #                                   inventory_line.product_qty)))
            inv.action_check()
            inv.write({'state': 'done'})
            self.post_inventory(inv)
        return True
