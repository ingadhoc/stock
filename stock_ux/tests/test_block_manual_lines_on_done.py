from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged
from odoo.tests.common import new_test_user


@tagged("post_install", "-at_install")
class TestBlockManualLinesOnDone(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        stock = cls.env.ref("stock.stock_location_stock")
        dest = cls.env["stock.location"].create({"name": "Dest 133672", "usage": "internal"})
        picking_type = cls.env.ref("stock.picking_type_internal")
        picking_type.write({"block_manual_lines": True, "block_additional_quantity": False})
        product = cls.env["product.product"].create({"name": "Product 133672", "is_storable": True})
        cls.env["stock.quant"]._update_available_quantity(product, stock, 3)
        # The check skips superuser, as _check_manual_lines does
        user = new_test_user(cls.env, login="stock_133672", groups="stock.group_stock_manager")
        cls.env = cls.env(user=user)
        cls.picking_a, cls.picking_b = cls.env["stock.picking"].create(
            [
                {
                    "picking_type_id": picking_type.id,
                    "location_id": stock.id,
                    "location_dest_id": dest.id,
                    "move_ids": [
                        (
                            0,
                            0,
                            {
                                "name": product.name,
                                "product_id": product.id,
                                "product_uom_qty": qty,
                                "location_id": stock.id,
                                "location_dest_id": dest.id,
                            },
                        )
                    ],
                }
                for qty in (2, 1)
            ]
        )
        (cls.picking_a | cls.picking_b).action_assign()

    def test_line_over_stock_blocks_validation(self):
        # Barcode raises the quantity of the existing line with a write
        self.picking_b.move_line_ids.write({"quantity": 2, "picked": True})
        with self.assertRaises(ValidationError):
            self.picking_b.button_validate()
        self.assertEqual(self.picking_a.move_line_ids.quantity, 2)

    def test_line_within_reservation_validates(self):
        self.picking_b.move_ids.picked = True
        self.picking_b.button_validate()
        self.assertEqual(self.picking_b.state, "done")
        self.assertEqual(self.picking_a.move_line_ids.quantity, 2)
