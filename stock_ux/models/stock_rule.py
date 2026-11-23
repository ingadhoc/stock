##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class StockRule(models.Model):
    _inherit = "stock.rule"

    propagate_carrier = fields.Boolean(compute="_compute_propagate_carrier", store=True, readonly=False)

    @api.depends("picking_type_id.code")
    def _compute_propagate_carrier(self):
        """Make True by default if picking code is outgoing"""
        for rec in self:
            rec.propagate_carrier = rec.picking_type_id.code == "outgoing"

    def _get_stock_move_values(
        self, product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values
    ):
        move_values = super()._get_stock_move_values(
            product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values
        )
        # El core marca to_refund=True para todo movimiento de cantidad negativa
        # ("If the quantity is negative the move should be considered as a
        # refund", stock_rule.py), asumiendo que un negativo es una devolucion.
        # Pero el negativo que genera "cancelar remanente" cancela mercaderia que
        # NUNCA se entrego al cliente: no es una devolucion. Al materializarse
        # como put-back interno (p.ej. Zona de picking -> Stock) ese to_refund
        # heredado infla las cantidades devueltas y el estado de facturacion de
        # la orden. En el flujo de cancelar remanente (cancel_from_order) ningun
        # movimiento generado es un refund. Ticket 127378.
        if self.env.context.get("cancel_from_order") and move_values.get("to_refund"):
            move_values["to_refund"] = False
        return move_values

    def _run_pull(self, procurements):
        """Backport from v19: recompute orderpoints after move creation for performance.

        Since qty_to_order_computed is now stored, we need to trigger its recomputation
        when moves are created to keep the stored values up to date.
        """
        result = super()._run_pull(procurements)

        # Extract orderpoints from procurements and recompute their qty_to_order_computed
        # procurement is a namedtuple:
        # (product_id, product_qty, product_uom, location_id, name, origin, company_id, values)
        orderpoints = self.env["stock.warehouse.orderpoint"]
        for procurement, rule in procurements:
            # Access values dict from the namedtuple (index 7 or .values attribute)
            values = procurement.values
            if values.get("orderpoint_id"):
                orderpoints |= values["orderpoint_id"]

        # Recompute only the affected orderpoints for performance
        if orderpoints:
            orderpoints.sudo()._compute_qty_to_order_computed()

        return result
