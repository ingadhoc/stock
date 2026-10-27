##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests.common import TransactionCase


class TestRemitoNumbering(TransactionCase):
    """Un remito ya numerado no vuelve a numerarse al reimprimirlo."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sequence = cls.env['ir.sequence'].create({
            'name': 'Test stock voucher',
            'code': 'stock.voucher',
            'prefix': '000X-',
            'padding': 8,
            'implementation': 'no_gap',
        })
        cls.book_auto = cls.env['stock.book'].create({
            'name': 'Autoimpreso test',
            'sequence_id': cls.sequence.id,
            'lines_per_voucher': 0,
            'autoprinted': True,
        })
        # Consumible: la validación no requiere stock disponible.
        cls.product = cls.env['product.product'].create(
            {'name': 'Producto remito test', 'type': 'consu'})
        cls.src = cls.env.ref('stock.stock_location_stock')
        cls.dest = cls.env.ref('stock.stock_location_customers')

    def _make_done_picking(self, book):
        picking_type = self.env.ref('stock.picking_type_out')
        picking_type.write({
            'book_required': True,
            'book_id': book.id,
            'voucher_required': False,
        })
        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': self.src.id,
            'location_dest_id': self.dest.id,
            'book_id': book.id,
            'move_ids': [(0, 0, {
                'name': self.product.name,
                'product_id': self.product.id,
                'product_uom_qty': 1.0,
                'product_uom': self.product.uom_id.id,
                'location_id': self.src.id,
                'location_dest_id': self.dest.id,
            })],
        })
        picking.action_confirm()
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
        picking.with_context(skip_sms=True).button_validate()
        return picking

    def test_print_and_assign_does_not_renumber(self):
        picking = self._make_done_picking(self.book_auto)
        self.assertEqual(len(picking.voucher_ids), 1)
        # Dos reintentos de impresión fallida: el remito conserva su número.
        picking.do_print_and_assign()
        picking.do_print_and_assign()
        self.assertEqual(len(picking.voucher_ids), 1)
