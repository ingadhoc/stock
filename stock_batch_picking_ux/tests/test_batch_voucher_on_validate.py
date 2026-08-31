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

    def test_incoming_batch_numbers_after_backorder_wizard(self):
        """El wizard de orden parcial valida por fuera del lote: el número tiene que quedar igual."""
        picking_type = self.env.ref("stock.picking_type_in")
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": self.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": self.src.id,
                "move_ids": [
                    (0, 0, {"name": self.product.name, "product_id": self.product.id, "product_uom_qty": 2.0})
                ],
            }
        )
        batch = self.env["stock.picking.batch"].create(
            {
                "picking_type_id": picking_type.id,
                "picking_ids": [(6, 0, picking.ids)],
                "voucher_number": "0001-00000456",
            }
        )
        batch.action_confirm()
        picking.move_ids.quantity = 1.0
        action = batch.action_done()
        self.assertFalse(picking.voucher_ids)

        self.env[action["res_model"]].with_context(**action["context"]).create({}).process()
        self.assertEqual(picking.voucher_ids.mapped("name"), ["0001-00000456"])
