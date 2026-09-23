<<<<<<< HEAD
||||||| MERGE BASE
=======
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestRemitoNumbering(TransactionCase):
    """Cuándo y cuántos números de remito se asignan según el talonario."""

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
                "lines_per_voucher": 2,
                "autoprinted": True,
            }
        )
        # Consumible: la validación no requiere stock disponible.
        cls.product = cls.env["product.product"].create({"name": "Producto remito test", "type": "consu"})
        cls.src = cls.env.ref("stock.stock_location_stock")
        cls.dest = cls.env.ref("stock.stock_location_customers")

    def _make_done_picking(self, book, book_required=True, nlines=1, validate=True, voucher_required=False):
        picking_type = self.env.ref("stock.picking_type_out")
        picking_type.write(
            {
                "book_required": book_required,
                "book_id": book.id,
                "voucher_required": voucher_required,
                # Gobierna la impresión, no la numeración.
                "auto_print_delivery_slip": False,
            }
        )
        # Productos distintos: los del mismo producto se agrupan en una línea.
        products = self.product
        if nlines > 1:
            products |= self.env["product.product"].create(
                [{"name": "Producto remito test %s" % index, "type": "consu"} for index in range(1, nlines)]
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
                            "name": product.name,
                            "product_id": product.id,
                            "product_uom_qty": 1.0,
                            "product_uom": product.uom_id.id,
                            "location_id": self.src.id,
                            "location_dest_id": self.dest.id,
                        },
                    )
                    for product in products
                ],
            }
        )
        picking.action_confirm()
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
        if validate:
            picking.with_context(skip_sms=True).button_validate()
        return picking

    def test_preprinted_not_numbered_on_validation(self):
        picking = self._make_done_picking(self.book_pre)
        self.assertEqual(picking.state, "done")
        self.assertFalse(picking.voucher_ids, "El preimpreso se numera al imprimir, por páginas reales.")

    def test_autoprinted_numbered_on_validation(self):
        # 3 líneas con 2 por remito estimarían 2: el autoimpreso lleva uno solo.
        picking = self._make_done_picking(self.book_auto, nlines=3)
        self.assertEqual(picking.state, "done")
        self.assertEqual(len(picking.voucher_ids), 1)

    def test_print_numbers_the_autoprinted_book(self):
        picking = self._make_done_picking(self.book_auto, book_required=False)
        picking.do_print_voucher()
        self.assertEqual(len(picking.voucher_ids), 1)

    def test_print_and_assign_does_not_renumber(self):
        picking = self._make_done_picking(self.book_auto)
        picking.do_print_and_assign()
        picking.do_print_and_assign()
        self.assertEqual(len(picking.voucher_ids), 1)

    def test_cai_range_is_inclusive_and_blocks_past_the_top(self):
        sequence = self.env["ir.sequence"].create(
            {
                "name": "Test stock voucher CAI",
                "code": "stock.voucher",
                "prefix": "0002-",
                "padding": 8,
                "implementation": "no_gap",
                "number_next": 100,
            }
        )
        book = self.env["stock.book"].create(
            {
                "name": "Autoimpreso con tope de CAI",
                "sequence_id": sequence.id,
                "lines_per_voucher": 0,
                "autoprinted": True,
                "sequence_to": "00000100",
            }
        )
        self.assertEqual(len(self._make_done_picking(book).voucher_ids), 1)
        with self.assertRaises(UserError):
            self._make_done_picking(book)

    def test_print_before_validation_does_not_number(self):
        """Imprimir el remito de un traslado sin validar no consume número."""
        picking = self._make_done_picking(self.book_auto, validate=False)
        picking.do_print_voucher()
        self.assertFalse(picking.voucher_ids)
        picking.with_context(skip_sms=True).button_validate()
        self.assertEqual(len(picking.voucher_ids), 1)

    def test_preprinted_not_numbered_before_validation(self):
        picking = self._make_done_picking(self.book_pre, validate=False)
        picking.assign_numbers(1, self.book_pre)
        self.assertFalse(picking.voucher_ids)
        picking.with_context(skip_sms=True).button_validate()
        picking.assign_numbers(1, self.book_pre)
        self.assertEqual(len(picking.voucher_ids), 1)

    def test_required_voucher_can_be_numbered_before_validation(self):
        # Sin numerar antes, un tipo con remito obligatorio no valida nunca.
        picking = self._make_done_picking(self.book_pre, validate=False, voucher_required=True)
        picking.assign_numbers(1, self.book_pre)
        picking.with_context(skip_sms=True).button_validate()
        self.assertEqual(picking.state, "done")

>>>>>>> FORWARD PORTED
