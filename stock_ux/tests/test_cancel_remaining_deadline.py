from datetime import timedelta

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "stock_ux_cancel_remaining")
class TestCancelRemainingDeadline(TransactionCase):
    """Ticket 125936: al cancelar remanente / bajar cantidad de un pedido que
    se editó DESPUES de confirmar, el `date_deadline` del movimiento pendiente
    queda desincronizado respecto del movimiento negativo de la baja. Como
    `date_deadline` estaba en la clave de neteo, no fusionaban y el negativo se
    daba vuelta como contraentrega (ingreso fantasma `to_refund`), dejando el
    pendiente huérfano. Excluimos `date_deadline` de la clave del negativo bajo
    `cancel_from_order` para que el neteo nativo cancele el pendiente.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.wh = cls.env["stock.warehouse"].create(
            {"name": "Test 3 Steps", "code": "T3S", "delivery_steps": "pick_pack_ship"}
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Test Storable 125936", "type": "consu", "is_storable": True}
        )
        cls.env["stock.quant"]._update_available_quantity(cls.product, cls.wh.lot_stock_id, 10)
        cls.partner = cls.env["res.partner"].create({"name": "Test Customer 125936"})

    def _confirmed_so(self, qty=2):
        so = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.wh.id,
                "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": qty})],
            }
        )
        so.action_confirm()
        return so

    def test_neg_key_excludes_date_deadline_only_under_cancel_from_order(self):
        Move = self.env["stock.move"]
        self.assertIn(
            "date_deadline",
            Move.with_context(cancel_from_order=True)._prepare_merge_negative_moves_excluded_distinct_fields(),
        )
        self.assertNotIn(
            "date_deadline",
            Move._prepare_merge_negative_moves_excluded_distinct_fields(),
        )

    def test_cancel_remaining_with_deadline_gap_nets_clean(self):
        so = self._confirmed_so(qty=2)
        line = so.order_line
        # Simular edición post-confirmación: el pendiente queda con deadline posterior
        # al del negativo que generará la baja (lo que rompía el neteo).
        for move in line.move_ids:
            if move.date_deadline:
                move.date_deadline = move.date_deadline + timedelta(minutes=10)

        # Bajar la cantidad (equivalente a cancelar remanente sobre lo no entregado).
        line.with_context(skip_locked_order_line_check=True).product_uom_qty = 0

        chain = self.env["stock.move"].search([("group_id", "=", so.procurement_group_id.id)])
        orphan = chain.filtered(
            lambda m: m.state not in ("done", "cancel") and not m.to_refund and m.product_qty > 0
        )
        refund = chain.filtered(lambda m: m.state not in ("done", "cancel") and m.to_refund)
        self.assertFalse(orphan, "Quedó un movimiento pendiente huérfano tras bajar la cantidad")
        self.assertFalse(refund, "Se generó una contraentrega / ingreso fantasma tras bajar la cantidad")
