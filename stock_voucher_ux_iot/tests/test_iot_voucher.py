##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestStockVoucherUxIot(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        cls.product = cls.env["product.product"].create(
            {
                "name": "Test Voucher Product",
                "type": "consu",
                "default_code": "TESTPROD1",
            }
        )

        cls.sequence = cls.env["ir.sequence"].create(
            {
                "name": "Test Remito Sequence",
                "code": "stock.voucher",
                "padding": 8,
                "number_next": 1,
                "implementation": "no_gap",
            }
        )
        cls.book = cls.env["stock.book"].create(
            {
                "name": "Test Preprinted Book",
                "sequence_id": cls.sequence.id,
                "lines_per_voucher": 0,
                "autoprinted": False,
                "company_id": cls.company.id,
            }
        )

        cls.picking_type_out = cls.env["stock.picking.type"].search(
            [("code", "=", "outgoing"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        cls.src_location = cls.picking_type_out.default_location_src_id or cls.env.ref("stock.stock_location_stock")
        cls.dest_location = cls.picking_type_out.default_location_dest_id or cls.env.ref(
            "stock.stock_location_customers"
        )

        # The aeroo remito report NGRSA prints through the IoT box. We only need
        # the record to exist; its rendering is mocked in the tests.
        cls.report = cls.env["ir.actions.report"].create(
            {
                "name": "Test Remito Preimpreso",
                "report_name": "remito_test",
                "report_type": "aeroo",
                "model": "stock.picking",
                "copies": 3,
            }
        )
        cls.report_cls = type(cls.report)

    def _new_picking(self, book=None):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_out.id,
                "location_id": self.src_location.id,
                "location_dest_id": self.dest_location.id,
                "book_id": (book or self.book).id,
            }
        )
        self.env["stock.move"].create(
            {
                "name": self.product.name,
                "product_id": self.product.id,
                "product_uom_qty": 1.0,
                "product_uom": self.product.uom_id.id,
                "picking_id": picking.id,
                "location_id": self.src_location.id,
                "location_dest_id": self.dest_location.id,
            }
        )
        return picking

    def test_iot_assigns_voucher_numbers(self):
        """Printing the preprinted remito through IoT assigns as many voucher
        numbers as real pages the report has."""
        picking = self._new_picking()
        self.assertFalse(picking.voucher_ids)
        with patch.object(self.report_cls, "_render", return_value=(b"%PDF-1.4 fake", "pdf")), patch.object(
            self.report_cls, "_count_voucher_pages", return_value=3
        ):
            self.report.render_and_send([], picking.ids)
        self.assertEqual(len(picking.voucher_ids), 3, "IoT print must assign one voucher per rendered page")

    def test_iot_is_idempotent_when_vouchers_exist(self):
        """A re-print through IoT must not burn extra sequence numbers."""
        picking = self._new_picking()
        picking.assign_numbers(2, self.book)
        self.assertEqual(len(picking.voucher_ids), 2)
        with patch.object(self.report_cls, "_render", return_value=(b"%PDF-1.4 fake", "pdf")), patch.object(
            self.report_cls, "_count_voucher_pages", return_value=5
        ):
            self.report.render_and_send([], picking.ids)
        self.assertEqual(len(picking.voucher_ids), 2, "Already numbered pickings must be left untouched")

    def test_iot_skips_autoprinted_book(self):
        """Autoprinted books are numbered on validation, not at print time."""
        autoprinted_book = self.env["stock.book"].create(
            {
                "name": "Test Autoprinted Book",
                "sequence_id": self.sequence.id,
                "lines_per_voucher": 0,
                "autoprinted": True,
                "company_id": self.company.id,
            }
        )
        picking = self._new_picking(book=autoprinted_book)
        with patch.object(self.report_cls, "_render", return_value=(b"%PDF-1.4 fake", "pdf")), patch.object(
            self.report_cls, "_count_voucher_pages", return_value=3
        ):
            self.report.render_and_send([], picking.ids)
        self.assertFalse(picking.voucher_ids, "Autoprinted books must not be numbered on the IoT print path")

    def test_iot_skips_non_remito_report(self):
        """A non-remito report must not trigger voucher assignment."""
        other_report = self.env["ir.actions.report"].create(
            {
                "name": "Test Other Aeroo",
                "report_name": "some_other_report",
                "report_type": "aeroo",
                "model": "stock.picking",
                "copies": 1,
            }
        )
        picking = self._new_picking()
        with patch.object(self.report_cls, "_render", return_value=(b"%PDF-1.4 fake", "pdf")), patch.object(
            self.report_cls, "_count_voucher_pages", return_value=3
        ):
            other_report.render_and_send([], picking.ids)
        self.assertFalse(picking.voucher_ids, "Only the remito report must assign voucher numbers")
