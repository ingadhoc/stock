from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestVoucherRequired(TransactionCase):
    def test_batch_voucher_number(self):
        """Alcanza sólo si el lote lo va a usar."""
        if "stock.picking.batch" not in self.env:
            self.skipTest("stock_picking_batch no instalado")
        picking_type = self.env.ref("stock.picking_type_in")
        picking_type.voucher_required = True
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": self.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": self.env.ref("stock.stock_location_stock").id,
            }
        )
        batch = self.env["stock.picking.batch"].create(
            {
                "picking_type_id": picking_type.id,
                "picking_ids": [(6, 0, picking.ids)],
                "voucher_number": "0001-00000123",
            }
        )
        picking.do_stock_voucher_transfer_check()

        batch.voucher_number = False
        with self.assertRaises(UserError):
            picking.do_stock_voucher_transfer_check()


class TestAssignNumbers(TransactionCase):
    def test_foreign_error_is_not_degraded(self):
        """Sólo se degrada el error del aviso de envío, no lo que ya estaba pendiente."""
        sequence = self.env["ir.sequence"].create(
            {"name": "Test", "code": "stock.voucher", "prefix": "0001-", "padding": 8}
        )
        book = self.env["stock.book"].create({"name": "Test", "sequence_id": sequence.id, "lines_per_voucher": 0})
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.env.ref("stock.picking_type_in").id,
                "location_id": self.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": self.env.ref("stock.stock_location_stock").id,
            }
        )

        def raise_foreign_error():
            raise UserError("ajeno al aviso de envío")

        with self.assertRaises(UserError):
            # el savepoint de assertRaises flushea al entrar: el pendiente se registra adentro
            self.env.cr.precommit.add(raise_foreign_error)
            picking.assign_numbers(1, book)
