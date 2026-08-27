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
