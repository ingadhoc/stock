from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestReturnAllUom(TransactionCase):
    """ "Devolver todo" debe devolver en la UdM del movimiento entregado.

    Backport del comportamiento de la 19: cuando la entrega está en una UdM
    distinta a la de referencia del producto (p.ej. con `stock.propagate_uom`
    activo, que deja las entregas en la UdM de la línea), la devolución hereda la
    UdM del movimiento y devuelve exactamente lo entregado, sin convertir a la UdM
    de referencia (que dejaba el remito en otra unidad y redondeaba de más). Ver
    ticket 125517.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.uom_dozen = cls.env.ref("uom.product_uom_dozen")
        cls.uom_unit = cls.env.ref("uom.product_uom_unit")
        cls.stock_location = cls.env.ref("stock.stock_location_stock")
        cls.customer_location = cls.env.ref("stock.stock_location_customers")
        cls.picking_type_out = cls.env.ref("stock.picking_type_out")

    def _deliver(self, product, uom, qty):
        """Confirma y valida una entrega de `qty` en `uom`, devuelve el picking hecho."""
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_out.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "name": product.name,
                            "product_id": product.id,
                            "product_uom": uom.id,
                            "product_uom_qty": qty,
                            "location_id": self.stock_location.id,
                            "location_dest_id": self.customer_location.id,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()
        move = picking.move_ids
        move.quantity = qty
        move.picked = True
        picking._action_done()
        self.assertEqual(move.state, "done")
        self.assertEqual(move.product_uom, uom)
        return picking

    def _return_all(self, picking):
        wizard = (
            self.env["stock.return.picking"]
            .with_context(active_id=picking.id, active_ids=picking.ids, active_model="stock.picking")
            .create({})
        )
        action = wizard.action_create_returns_all()
        return self.env["stock.picking"].browse(action["res_id"]).move_ids

    def test_return_all_keeps_move_uom(self):
        """Entrega en Unidades de un producto con referencia en Docenas -> la
        devolución queda en Unidades (misma UdM que la entrega), no en Docenas.

        Sin el fix el core copiaba el número crudo (24) interpretándolo en la UdM
        de referencia, así que salían 24 Docenas.
        """
        product = self.env["product.product"].create(
            {
                "name": "Producto con referencia en docenas",
                "is_storable": True,
                "uom_id": self.uom_dozen.id,
                "uom_po_id": self.uom_dozen.id,
            }
        )
        picking = self._deliver(product, self.uom_unit, 24)
        return_move = self._return_all(picking)
        self.assertEqual(return_move.product_uom, self.uom_unit)
        self.assertEqual(return_move.product_uom_qty, 24.0)

    def test_return_all_no_overreturn_on_non_exact_ratio(self):
        """Ratio no exacto: devolver 1 Unidad de un producto con referencia en
        Docenas no debe devolver de más.

        Convertir a Docenas redondeaba 1/12 hacia arriba (0,09 Docenas = 1,08
        Unidades). Heredando la UdM del movimiento la devolución es 1 Unidad exacta.
        """
        product = self.env["product.product"].create(
            {
                "name": "Producto docenas ratio no exacto",
                "is_storable": True,
                "uom_id": self.uom_dozen.id,
                "uom_po_id": self.uom_dozen.id,
            }
        )
        picking = self._deliver(product, self.uom_unit, 1)
        return_move = self._return_all(picking)
        self.assertEqual(return_move.product_uom, self.uom_unit)
        self.assertEqual(return_move.product_uom_qty, 1.0)
