##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCancelRemainingPushDomain(TransactionCase):
    """Entrega multi paso cuya regla de push esta desdoblada en variantes
    condicionadas por `push_domain` sobre datos de los move lines.

    El core empuja el movimiento positivo en `_action_done` (el move de origen
    ya tiene move lines) y el espejo negativo del cancel remanente en
    `_action_confirm` (todavia sin move lines). Con un `push_domain` que lee
    `move_line_ids`, las dos evaluaciones no resuelven la misma regla: el
    espejo nace en otro tipo de operacion, no llega a ser candidato del merge,
    no netea y el movimiento del tramo siguiente queda huerfano y vivo.

    El escenario de control (una sola regla de push, sin dominio) documenta el
    comportamiento esperado: el espejo netea y el tramo siguiente se cancela.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer_loc = cls.env.ref("stock.stock_location_customers")
        cls.product = cls.env["product.product"].create(
            {"name": "Test Push Domain", "type": "consu", "is_storable": True}
        )
        cls.partner = cls.env["res.partner"].create({"name": "Test Push Domain Customer"})

    def _build_warehouse(self, code, split_push):
        """Almacen de 2 pasos con ruta pull + push.

        Con `split_push` la regla de push se desdobla en dos variantes que
        difieren solo en el tipo de operacion, condicionadas por un dato de los
        move lines del movimiento que se empuja.
        """
        warehouse = self.env["stock.warehouse"].create(
            {"name": "Test Push Domain %s" % code, "code": code, "delivery_steps": "pick_ship"}
        )
        route = warehouse.delivery_route_id
        route.rule_ids.unlink()
        rule_vals = {
            "route_id": route.id,
            "warehouse_id": warehouse.id,
            "company_id": warehouse.company_id.id,
        }
        # Pull: la dispara la demanda de la orden (destino Cliente). El move va
        # Stock -> Salida (destino del tipo de operacion) con location_final Cliente.
        self.env["stock.rule"].create(
            {
                **rule_vals,
                "name": "Test Stock -> Customers (pull)",
                "sequence": 10,
                "action": "pull",
                "procure_method": "make_to_stock",
                "location_src_id": warehouse.lot_stock_id.id,
                "location_dest_id": self.customer_loc.id,
                "location_dest_from_rule": False,
                "picking_type_id": warehouse.pick_type_id.id,
            }
        )
        push_vals = {
            **rule_vals,
            "action": "push",
            "procure_method": "make_to_order",
            "location_src_id": warehouse.wh_output_stock_loc_id.id,
            "location_dest_id": self.customer_loc.id,
        }
        if split_push:
            reserved_from = "[('move_line_ids.location_id', '%s', [%s])]"
            self.env["stock.rule"].create(
                {
                    **push_vals,
                    "name": "Test Output -> Customers (push, reserved)",
                    "sequence": 20,
                    "picking_type_id": warehouse.out_type_id.id,
                    "push_domain": reserved_from % ("in", warehouse.lot_stock_id.id),
                }
            )
            self.env["stock.rule"].create(
                {
                    **push_vals,
                    "name": "Test Output -> Customers (push, not reserved)",
                    "sequence": 30,
                    "picking_type_id": warehouse.out_type_id.copy(
                        {
                            "name": "Delivery Orders Alt",
                            "sequence_code": "OUTALT",
                            "warehouse_id": warehouse.id,
                        }
                    ).id,
                    "push_domain": reserved_from % ("not in", warehouse.lot_stock_id.id),
                }
            )
        else:
            self.env["stock.rule"].create(
                {
                    **push_vals,
                    "name": "Test Output -> Customers (push)",
                    "sequence": 20,
                    "picking_type_id": warehouse.out_type_id.id,
                }
            )
        self.env["stock.quant"]._update_available_quantity(self.product, warehouse.lot_stock_id, 100)
        return warehouse

    def _moves_report(self, order, label):
        moves = self.env["stock.move"].search(
            [("product_id", "=", self.product.id), ("company_id", "=", order.company_id.id)], order="id"
        )
        report = ["--- %s ---" % label]
        for move in moves:
            report.append(
                "  move %s picking=%s type=%s %s -> %s final=%s qty=%s state=%s to_refund=%s"
                % (
                    move.id,
                    move.picking_id.name or "-",
                    move.picking_type_id.name or "-",
                    move.location_id.name,
                    move.location_dest_id.name,
                    move.location_final_id.name or "-",
                    move.product_uom_qty,
                    move.state,
                    move.to_refund,
                )
            )
        return "\n".join(report)

    def _cancel_remaining_after_first_step(self, code, split_push):
        warehouse = self._build_warehouse(code, split_push)
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": warehouse.id,
                "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": 10})],
            }
        )
        order.action_confirm()
        report = [self._moves_report(order, "%s: orden confirmada" % code)]

        picking = order.picking_ids.filtered(lambda p: p.picking_type_id == warehouse.pick_type_id)
        self.assertTrue(picking, "no se creo el primer paso\n" + "\n".join(report))
        picking.action_assign()
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
            move.picked = True
        picking.button_validate()
        report.append(self._moves_report(order, "%s: primer paso validado" % code))

        next_step = order.order_line.move_ids.filtered(
            lambda m: m.location_dest_id == self.customer_loc and m.state not in ("done", "cancel")
        )
        self.assertTrue(next_step, "no se empujo el tramo siguiente\n" + "\n".join(report))

        order.order_line.with_context(cancel_from_order=True).button_cancel_remaining()
        report.append(self._moves_report(order, "%s: remanente cancelado" % code))
        return next_step, "\n".join(report)

    def test_cancel_remaining_cancels_next_step(self):
        """Control: con una sola regla de push el espejo netea el tramo siguiente."""
        next_step, report = self._cancel_remaining_after_first_step("TPDA", split_push=False)
        self.assertEqual(next_step.state, "cancel", "el tramo siguiente deberia quedar cancelado\n" + report)

    def test_cancel_remaining_cancels_next_step_with_push_domain(self):
        """El espejo hereda la puerta del tramo que deshace y netea igual."""
        next_step, report = self._cancel_remaining_after_first_step("TPDB", split_push=True)
        self.assertEqual(next_step.state, "cancel", "el tramo siguiente deberia quedar cancelado\n" + report)
