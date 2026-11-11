##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class StockRequest(models.Model):
    _inherit = "stock.request"

    order_id = fields.Many2one(
        ondelete="cascade",
    )

    @api.onchange("product_id")
    def onchange_product_id(self):
        res = super().onchange_product_id()
        if self.order_id.route_id.id in self.route_ids.ids:
            self.route_id = self.order_id.route_id.id
        return res

    # DEPRECATED def action_cancel(self):

    def button_cancel_remaining(self):
        for rec in self:
            old_product_uom_qty = rec.product_uom_qty
            # we need to do this using direct write because this constraints "_check_type" in original module.
            rec._write({"product_uom_qty": rec.qty_done})
            # _write does not refresh the cache and check_done would read the old quantity
            rec.invalidate_recordset(["product_uom_qty"])
            # a return in progress is not part of what the line still has pending
            pending_moves = rec.move_ids.filtered(
                lambda x: x.state not in ["done", "cancel"] and not x.origin_returned_move_id
            )
            # lines of the same product share the move, so a shared move only gives up what this line has pending
            shared_allocations = rec.allocation_ids.filtered(
                lambda a: a.stock_move_id in pending_moves
                and any(
                    other.stock_request_id != rec and other.open_product_qty > 0
                    for other in a.stock_move_id.allocation_ids
                )
            )
            lowered_moves = shared_allocations.stock_move_id | self._get_pending_orig_moves(
                shared_allocations.stock_move_id
            )
            reserved_moves = lowered_moves.filtered(lambda m: m.state in ["assigned", "partially_available"])
            product_uom = rec.product_id.uom_id
            emptied_moves = self.env["stock.move"]
            for allocation in shared_allocations:
                move = allocation.stock_move_id
                open_qty = allocation.open_product_qty
                allocation.requested_product_uom_qty -= product_uom._compute_quantity(open_qty, rec.product_uom_id)
                for chain_move in move | self._get_pending_orig_moves(move):
                    new_qty = chain_move.product_uom_qty - product_uom._compute_quantity(open_qty, chain_move.uom_id)
                    if chain_move.uom_id.compare(new_qty, 0) > 0:
                        chain_move.product_uom_qty = new_qty
                    else:
                        emptied_moves |= chain_move
            # the stored quantities do not depend on the requested quantity of the allocations
            rec._compute_qty()
            # lowering the demand unreserves the whole move, the other lines still need it
            (reserved_moves - emptied_moves)._action_assign()
            ((pending_moves - lowered_moves) | emptied_moves)._action_cancel()
            rec.order_id.message_post(
                body=self.env._('Cancel remaining call for line "%s" (id %s), line qty updated from %s to %s')
                % (rec.name, rec.id, old_product_uom_qty, rec.qty_done)
            )
            rec.check_done()

    @api.model
    def _get_pending_orig_moves(self, moves):
        """Moves that feed the given ones through the route (previous steps) and are not finished."""
        # iterative with the visited moves, move_orig_ids can form cycles with returns
        orig_moves = self.env["stock.move"]
        to_visit = moves
        while to_visit:
            to_visit = to_visit.move_orig_ids.filtered(lambda m: m.state not in ["done", "cancel"]) - orig_moves - moves
            orig_moves |= to_visit
        return orig_moves

    def _prepare_procurement_values(self, reference_ids=False):
        values = super()._prepare_procurement_values(reference_ids=reference_ids)
        # Si la línea pertenece a una orden y no se cargaron referencias a mano,
        # inyectamos una referencia por defecto por orden para que todas las
        # líneas se agrupen en un único picking (ver
        # StockRequestOrder._get_default_stock_reference). En Odoo 19 el
        # agrupamiento se basa en reference_ids, no en el procurement group.
        if self.order_id and not values.get("reference_ids"):
            values["reference_ids"] = self.order_id._get_default_stock_reference()
        return values

    def _action_launch_procurement_rule(self):
        """TODO we could create an option or check if procurement_jit
        is installed
        """
        res = super()._action_launch_procurement_rule()
        # Las líneas de una orden comparten picking (ver _prepare_procurement_values), así que
        # reasignar línea por línea libera y reserva el mismo picking una vez por línea.
        reassign = (
            self.mapped("picking_ids")
            .filtered(lambda x: x.state == "confirmed" or (x.state in ["waiting", "assigned"] and not x.printed))
            .sudo()
        )
        if reassign:
            reassign.do_unreserve()
            reassign.action_assign()
        return res
