from odoo.exceptions import UserError
from odoo.tests import new_test_user, tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestInventoryLocationMoves(TransactionCase):
    """Moving stock from or to the inventory adjustment location is an adjustment:
    without the Inventory Adjustments group it is refused, while scrapping is not."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.basic_user = new_test_user(cls.env, login="inv_loc_basic", groups="stock.group_stock_user")
        cls.adjust_user = new_test_user(
            cls.env,
            login="inv_loc_adjust",
            groups="stock.group_stock_user,stock_ux.group_stock_inventory_adjustment",
        )
        cls.product = cls.env["product.product"].create({"name": "Inventory location product", "is_storable": True})
        cls.stock_location = cls.env.ref("stock.warehouse0").lot_stock_id
        cls.inventory_location = cls.product.with_company(cls.stock_location.company_id).property_stock_inventory
        cls.customer_location = cls.env.ref("stock.stock_location_customers")
        cls.env["stock.quant"]._update_available_quantity(cls.product, cls.stock_location, 10)

    def _move(self, location, location_dest):
        move = self.env["stock.move"].create(
            {
                "product_id": self.product.id,
                "product_uom_qty": 2,
                "location_id": location.id,
                "location_dest_id": location_dest.id,
            }
        )
        move._action_confirm()
        move.write({"quantity": 2, "picked": True})
        return move

    def test_user_without_adjustment_cannot_move_from_inventory_location(self):
        move = self._move(self.inventory_location, self.stock_location)
        with self.assertRaises(UserError):
            move.with_user(self.basic_user)._action_done()

    def test_user_without_adjustment_cannot_move_to_inventory_location(self):
        move = self._move(self.stock_location, self.inventory_location)
        with self.assertRaises(UserError):
            move.with_user(self.basic_user)._action_done()

    def test_user_with_adjustment_moves_from_inventory_location(self):
        move = self._move(self.inventory_location, self.stock_location)
        move.with_user(self.adjust_user)._action_done()
        self.assertEqual(move.state, "done")
        self.assertEqual(self.product.with_context(location=self.stock_location.id).qty_available, 12)

    def test_user_without_adjustment_scraps(self):
        scrap_location = self.stock_location.company_id.scrap_location_id
        move = self._move(self.stock_location, scrap_location)
        move.with_user(self.basic_user)._action_scrap()
        self.assertEqual(move.state, "done")
        self.assertTrue(move.is_scrap)

    def test_user_without_adjustment_removes_repair_parts(self):
        if "repair_id" not in self.env["stock.move"]._fields:
            self.skipTest("repair is not installed")
        repair = self.env["repair.order"].create({"product_id": self.product.id})
        move = self.env["stock.move"].create(
            {
                "product_id": self.product.id,
                "product_uom_qty": 2,
                "repair_id": repair.id,
                "repair_line_type": "remove",
            }
        )
        self.assertEqual(move.location_dest_id.usage, "inventory")
        move._action_confirm()
        move.write({"quantity": 2, "picked": True})
        move.with_user(self.basic_user)._action_done()
        self.assertEqual(move.state, "done")

    def test_user_without_adjustment_delivers(self):
        move = self._move(self.stock_location, self.customer_location)
        move.with_user(self.basic_user)._action_done()
        self.assertEqual(move.state, "done")
