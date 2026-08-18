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

    def action_create_returns_all(self):
        # "Devolver todo" debe dejar la devolución en la UdM del movimiento que
        # revierte (como la 19), no en la UdM de referencia del producto. El
        # cálculo de cantidades y el redondeo los sigue haciendo el core; acá solo
        # pasamos un flag de contexto para que `_prepare_move_default_values`
        # herede la UdM del movimiento. Ese cambio aplica únicamente cuando la
        # entrega quedó en una UdM distinta a la de referencia (p.ej. con
        # "Propagar UdM" activo); el "Devolver" manual y las devoluciones sin
        # diferencia de UdM corren el core intacto. Ver ticket 125517.
        return super(StockReturnPicking, self.with_context(return_all_move_uom=True)).action_create_returns_all()


class StockReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"

    def _prepare_move_default_values(self, new_picking):
        vals = super()._prepare_move_default_values(new_picking)
        # Solo cuando "Devolver todo" lo pide (contexto) y solo si la entrega está
        # en una UdM distinta a la de referencia: el movimiento de devolución
        # hereda la UdM del movimiento original en vez de forzar la de referencia.
        # Fuera de ese caso (Devolver manual, o sin diferencia de UdM) se respeta
        # el comportamiento del core. Ver ticket 125517.
        move = self.move_id
        if self.env.context.get("return_all_move_uom") and move and move.product_uom != self.product_id.uom_id:
            vals["product_uom"] = move.product_uom.id
        return vals
