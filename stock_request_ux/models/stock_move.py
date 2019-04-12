##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models, fields


class StockMove(models.Model):
    _inherit = 'stock.move'

    request_order_id = fields.Many2one(
        related='stock_request_ids.order_id',
        readonly=True,
    )

    def _split(self, qty, restrict_partner_id=False):
        """ When we are on a move created by a stock_request and we create a
        backorder, we create a new allocation linked to this new move and
        update quantities
        """
        new_move_id = super(StockMove, self)._split(
            qty, restrict_partner_id=restrict_partner_id)

        remaining_to_allocate = qty
        for allocation in self.allocation_ids:
            if not remaining_to_allocate:
                break
            to_allocate = min(
                remaining_to_allocate, allocation.requested_product_uom_qty)
            remaining_to_allocate -= to_allocate

            allocation.copy({
                'stock_move_id': new_move_id,
                'requested_product_uom_qty': to_allocate,
            })
            allocation.requested_product_uom_qty -= to_allocate

        return new_move_id
