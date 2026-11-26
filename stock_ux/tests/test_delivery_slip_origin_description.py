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
        cls.params.set_bool("stock_ux.delivery_slip_use_origin", True)
        cls.partner = cls.env["res.partner"].create({"name": "Customer"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Waterproof Power Supply",
                "default_code": "PS-24",
                "is_storable": True,
            }
        )
        cls.picking_type = cls.env.ref("stock.picking_type_out")
        cls.stock_location = cls.env.ref("stock.stock_location_stock")
        cls.customer_location = cls.env.ref("stock.stock_location_customers")

    def _get_properties(self, line_name):
        # the transfer is built by hand: sale exception rules of other modules can stop
        # action_confirm, and then no delivery would be created
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
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type.id,
                "partner_id": self.partner.id,
                "origin": order.name,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
            }
        )
        move = self.env["stock.move"].create(
            {
                "picking_id": picking.id,
                "product_id": self.product.id,
                "product_uom_qty": 1,
                "sale_line_id": order.order_line.id,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
            }
        )
        move_line = self.env["stock.move.line"].create(
            {
                "move_id": move.id,
                "picking_id": picking.id,
                "product_id": self.product.id,
                "quantity": 1,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
            }
        )
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
        self.params.set_bool("stock_ux.delivery_slip_origin_only", True)
        properties = self._get_properties("Installation service\nThird floor")
        self.assertEqual(properties["name"], "Installation service")
        self.assertEqual(properties["description"], "Third floor")
