##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import api, models, fields


class StockMove(models.Model):
    _inherit = 'stock.move'

    request_order_id = fields.Many2one(
        related='stock_request_ids.order_id',
    )

    def _split(self, qty, restrict_partner_id=False):
        """ When we are on a move created by a stock_request and we create a
        backorder, we send by vals of moves the allocation to copy and the qty to allocate.
        """
        move_val_list = super()._split(qty, restrict_partner_id=restrict_partner_id)
        remaining_to_allocate = qty
        for allocation in self.allocation_ids:
            if not remaining_to_allocate:
                break
            to_allocate = min(
                remaining_to_allocate, allocation.requested_product_uom_qty)
            remaining_to_allocate -= to_allocate
            for val in move_val_list:
                val['allocation'] = (allocation, to_allocate)
            allocation.requested_product_uom_qty -= to_allocate

        return move_val_list
    
    @api.model
    def create(self, vals):
        """ When we are on a move created by a stock_request and we create a
        backorder, we create a new allocation linked to this new move and
        update quantities
        """
        if vals.get('allocation'):
            allocation,  qty = vals.pop('allocation')
            res = super().create(vals)
            allocation.copy({
                    'stock_move_id': res.id,
                    'requested_product_uom_qty': qty,
                })
            return res
        else:
            return super().create(vals)
        
