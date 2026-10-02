from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "stock_ux_cancel_remaining")
class TestCancelRemainingPrice(TransactionCase):
    """Al cancelar remanente / bajar cantidad, el movimiento negativo de la baja
    se construye "fresco" y puede traer un `price_unit` distinto al del pendiente
    original (si cambió el costo/replenishment del producto, o por descuento en
    compras). Como `price_unit` estaba en la clave de neteo, esa diferencia
    rompía el neteo y, en vez de cancelar el pendiente, se generaba una
    contraentrega. Lo excluimos de la clave del negativo bajo `cancel_from_order`
    para que el neteo nativo cancele el pendiente igual (el core recalcula el
    precio promedio ponderado al absorber).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.wh = cls.env["stock.warehouse"].create(
            {"name": "Test Price 2S", "code": "TP2", "delivery_steps": "pick_ship"}
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Test Storable price", "type": "consu", "is_storable": True, "standard_price": 10}
        )
        cls.env["stock.quant"]._update_available_quantity(cls.product, cls.wh.lot_stock_id, 10)
        cls.partner = cls.env["res.partner"].create({"name": "Test Customer price"})

    def test_neg_key_excludes_price_unit_only_under_cancel_from_order(self):
        Move = self.env["stock.move"]
        self.assertIn(
            "price_unit",
            Move.with_context(cancel_from_order=True)._prepare_merge_negative_moves_excluded_distinct_fields(),
        )
        self.assertNotIn(
            "price_unit",
            Move._prepare_merge_negative_moves_excluded_distinct_fields(),
        )

    def test_cancel_remaining_with_price_gap_nets_clean(self):
        so = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.wh.id,
                "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": 2})],
            }
        )
        so.action_confirm()
        line = so.order_line
        # Simular costo distinto en el pendiente respecto del negativo que generará la baja.
        for move in line.move_ids.filtered(lambda m: m.state not in ("done", "cancel")):
            move.price_unit = 77.0

        line.with_context(skip_locked_order_line_check=True).product_uom_qty = 0

        chain = self.env["stock.move"].search([("group_id", "=", so.procurement_group_id.id)])
        orphan = chain.filtered(lambda m: m.state not in ("done", "cancel") and not m.to_refund and m.product_qty > 0)
        refund = chain.filtered(lambda m: m.state not in ("done", "cancel") and m.to_refund)
        self.assertFalse(orphan, "Quedó un movimiento pendiente huérfano tras bajar la cantidad")
        self.assertFalse(refund, "Se generó una contraentrega / ingreso fantasma tras bajar la cantidad")
