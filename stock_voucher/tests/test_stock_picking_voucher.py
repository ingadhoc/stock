from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestStockPickingVoucherFormatting(TransactionCase):
    def setUp(self):
        super(TestStockPickingVoucherFormatting, self).setUp()
        self.StockPickingVoucher = self.env["stock.picking.voucher"]

    def test_format_document_number(self):
        valid_number = "0001-00000001"
        invalid_number = "12345-123456789"
        formatted_number = self.StockPickingVoucher._format_document_number(valid_number)
        self.assertEqual(formatted_number, "0001-00000001")

        with self.assertRaises(UserError):
            self.StockPickingVoucher._format_document_number(invalid_number)
