<<<<<<< HEAD
||||||| MERGE BASE
=======
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests.common import TransactionCase


class TestRemitoPreimpresoNumbering(TransactionCase):
    """Numeración de remitos según el tipo de talonario.

    Preimpreso (``autoprinted=False``): NO se numera en la validación por la
    estimación ``lines_per_voucher`` (subnumera). La cantidad se determina al
    imprimir, según las páginas reales del reporte (controller).

    Autoimpreso (``autoprinted=True``): se numera en la validación sólo si el
    tipo de operación pide imprimir el remito al validar
    (``auto_print_delivery_slip``) — el remito reemplaza al recibo de entrega
    nativo. Sin ese flag no se numera al validar (se asigna al imprimir a mano).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sequence = cls.env["ir.sequence"].create(
            {
                "name": "Test stock voucher",
                "code": "stock.voucher",
                "prefix": "0001-",
                "padding": 8,
                "implementation": "no_gap",
            }
        )
        cls.book_pre = cls.env["stock.book"].create(
            {
                "name": "Preimpreso test",
                "sequence_id": cls.sequence.id,
                "lines_per_voucher": 25,
                "autoprinted": False,
            }
        )
        cls.book_auto = cls.env["stock.book"].create(
            {
                "name": "Autoimpreso test",
                "sequence_id": cls.sequence.id,
                "lines_per_voucher": 0,
                "autoprinted": True,
            }
        )
        # Consumible no almacenable: la validación no requiere stock disponible.
        cls.product = cls.env["product.product"].create(
            {
                "name": "Producto remito test",
                "type": "consu",
            }
        )
        cls.src = cls.env.ref("stock.stock_location_stock")
        cls.dest = cls.env.ref("stock.stock_location_customers")

    def _make_done_picking(self, book, auto_print=False):
        picking_type = self.env.ref("stock.picking_type_out")
        picking_type.write(
            {
                "book_required": True,
                "book_id": book.id,
                "voucher_required": False,
                "auto_print_delivery_slip": auto_print,
            }
        )
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": self.src.id,
                "location_dest_id": self.dest.id,
                "book_id": book.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "name": self.product.name,
                            "product_id": self.product.id,
                            "product_uom_qty": 1.0,
                            "product_uom": self.product.uom_id.id,
                            "location_id": self.src.id,
                            "location_dest_id": self.dest.id,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
        picking.with_context(skip_sms=True).button_validate()
        return picking

    def test_preprinted_not_preassigned_on_validation(self):
        picking = self._make_done_picking(self.book_pre)
        self.assertEqual(picking.state, "done")
        self.assertFalse(
            picking.voucher_ids,
            "Un talonario preimpreso no debe pre-numerarse por estimación en _action_done; "
            "la numeración se hace al imprimir según páginas reales.",
        )

    def test_autoprinted_assigned_on_validation_with_flag(self):
        # Con auto_print_delivery_slip el remito reemplaza al recibo de entrega
        # y el autoimpreso se numera al validar.
        picking = self._make_done_picking(self.book_auto, auto_print=True)
        self.assertEqual(picking.state, "done")
        self.assertEqual(
            len(picking.voucher_ids),
            1,
            "Un talonario autoimpreso debe asignar un único remito en la validación "
            "cuando el tipo de operación tiene auto_print_delivery_slip.",
        )

    def test_autoprinted_not_assigned_without_flag(self):
        # Sin el flag, validar no numera: el número se asigna al imprimir a mano.
        picking = self._make_done_picking(self.book_auto, auto_print=False)
        self.assertEqual(picking.state, "done")
        self.assertFalse(
            picking.voucher_ids,
            "Sin auto_print_delivery_slip, un talonario autoimpreso no debe numerarse "
            "en la validación; el número se asigna al imprimir.",
        )

>>>>>>> FORWARD PORTED
