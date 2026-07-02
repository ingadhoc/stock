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
            to_cancel_moves = rec.move_ids.filtered(lambda x: x.state not in ["done", "cancel"])
            # to_cancel_moves.cancel_move()
            # if float_compare(qty_done, request.product_uom_qty,
            # si se agrega mismo producto en los request se re-utiliza mismo
            # move que queda vinculado a los allocation, por eso mandamos a
            # cancelar solo la cantidad en progreso (para que no cancele
            # cosas que ya se entregaron parcialmente)
            to_cancel_moves._action_cancel()
            rec.order_id.message_post(
                body=self.env._('Cancel remaining call for line "%s" (id %s), line qty updated from %s to %s')
                % (rec.name, rec.id, old_product_uom_qty, rec.qty_done)
            )
            rec.check_done()

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
        for rec in self:
            reassign = rec.picking_ids.filtered(
                lambda x: x.state == "confirmed" or (x.state in ["waiting", "assigned"] and not x.printed)
            ).sudo()
            if reassign:
                reassign.do_unreserve()
                reassign.action_assign()
        return res
