##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeliverySlipOriginDescription(TransactionCase):
    """With delivery_slip_use_origin the delivery slip prints the product with its code and,
    below, what the origin description adds to it; delivery_slip_origin_only prints the
    origin description alone."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.params = cls.env["ir.config_parameter"].sudo()
        cls.params.set_param("stock_ux.delivery_slip_use_origin", "True")
        cls.partner = cls.env["res.partner"].create({"name": "Customer"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Waterproof Power Supply",
                "default_code": "PS-24",
                "is_storable": True,
            }
        )

    def _get_properties(self, line_name):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": line_name,
                            "product_uom_qty": 1,
                        },
                    )
                ],
            }
        )
        order.action_confirm()
        move = order.picking_ids.move_ids
        move.quantity = 1
        move_line = move.move_line_ids
        return move_line._get_aggregated_properties(move_line=move_line)

    def test_line_with_note_keeps_the_product(self):
        properties = self._get_properties("[PS-24] Waterproof Power Supply\nWarranty replacement")
        self.assertEqual(properties["name"], "[PS-24] Waterproof Power Supply")
        self.assertEqual(properties["description"], "Warranty replacement")

    def test_line_without_note(self):
        properties = self._get_properties("[PS-24] Waterproof Power Supply")
        self.assertEqual(properties["name"], "[PS-24] Waterproof Power Supply")
        self.assertEqual(properties["description"], "")

    def test_rewritten_description_goes_below_the_product(self):
        properties = self._get_properties("Installation service\nThird floor")
        self.assertEqual(properties["name"], "[PS-24] Waterproof Power Supply")
        self.assertEqual(properties["description"], "Installation service\nThird floor")

    def test_origin_only_prints_the_origin_description_alone(self):
        self.params.set_param("stock_ux.delivery_slip_origin_only", "True")
        properties = self._get_properties("Installation service\nThird floor")
        self.assertEqual(properties["name"], "Installation service")
        self.assertEqual(properties["description"], "Third floor")
