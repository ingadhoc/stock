from odoo.tests import Form, TransactionCase, tagged
from odoo.tools import mute_logger
from psycopg2 import IntegrityError


@tagged("post_install", "-at_install")
class TestRepairPartner(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Repair customer"})
        cls.order = cls.env["sale.order"].create({"partner_id": cls.partner.id})

    def test_partner_in_repair_cannot_be_deleted(self):
        partner = self.env["res.partner"].create({"name": "Duplicated customer"})
        self.env["repair.order"].create({"partner_id": partner.id})
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"), self.cr.savepoint():
            partner.unlink()

    def test_empty_partner_editable_with_sale_order(self):
        repair = self.env["repair.order"].create({"sale_order_id": self.order.id})
        with Form(repair) as form:
            form.partner_id = self.partner
        self.assertEqual(repair.partner_id, self.partner)

    def test_partner_readonly_with_sale_order(self):
        repair = self.env["repair.order"].create({"partner_id": self.partner.id, "sale_order_id": self.order.id})
        other = self.env["res.partner"].create({"name": "Other customer"})
        with Form(repair) as form, self.assertRaises(AssertionError):
            form.partner_id = other
