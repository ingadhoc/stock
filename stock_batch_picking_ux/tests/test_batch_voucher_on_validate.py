##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestBatchVoucherOnValidate(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.book = cls.env["stock.book"].create(
            {
                "name": "Talonario lote test",
                "sequence_id": cls.env["ir.sequence"]
                .create(
                    {
                        "name": "Test batch voucher",
                        "code": "stock.voucher.batch.test",
                        "prefix": "0001-",
                        "padding": 8,
                        "implementation": "no_gap",
                    }
                )
                .id,
                "lines_per_voucher": 0,
            }
        )
        cls.product = cls.env["product.product"].create({"name": "Producto lote remito test", "type": "consu"})
        cls.src = cls.env.ref("stock.stock_location_stock")
        cls.dest = cls.env.ref("stock.stock_location_customers")
        cls.picking_type = cls.env.ref("stock.picking_type_out")
        cls.picking_type.write(
            {
                "book_required": True,
                "book_id": cls.book.id,
                "voucher_required": False,
                "auto_print_delivery_slip": True,
            }
        )

    def _new_batch(self):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type.id,
                "location_id": self.src.id,
                "location_dest_id": self.dest.id,
                "book_id": self.book.id,
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
        picking.action_assign()
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
            move.picked = True
        batch = self.env["stock.picking.batch"].create(
            {
                "picking_type_id": self.picking_type.id,
                "picking_ids": [(6, 0, picking.ids)],
            }
        )
        batch.action_confirm()
        return batch, picking

    def test_voucher_only_for_validated_picking_and_once(self):
        """Una validación abortada no numera y el reintento numera una sola vez."""
        batch, picking = self._new_batch()
        blocked_action = {"type": "ir.actions.act_window", "res_model": "stock.picking"}
        with patch.object(type(picking), "button_validate", lambda self, *a, **k: blocked_action):
            batch.action_done()
        self.assertNotEqual(picking.state, "done")
        self.assertFalse(picking.voucher_ids)

        batch.action_done()
        self.assertEqual(picking.state, "done")
        self.assertEqual(len(picking.voucher_ids), 1)
