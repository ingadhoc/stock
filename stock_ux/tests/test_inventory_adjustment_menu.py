from odoo.tests import new_test_user, tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestInventoryAdjustmentMenu(TransactionCase):
    """Physical Inventory is only offered to users who can adjust: an Inventory User
    without the adjustment permission got the menu and an access error behind it."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.menu = cls.env.ref("stock.menu_action_inventory_tree")
        cls.basic_user = new_test_user(cls.env, login="inv_basic", groups="stock.group_stock_user")
        cls.adjust_user = new_test_user(
            cls.env,
            login="inv_adjust",
            groups="stock.group_stock_user,stock_ux.group_stock_inventory_adjustment",
        )

    def _visible(self, user):
        return self.menu.id in self.env["ir.ui.menu"].with_user(user)._visible_menu_ids()

    def test_inventory_user_without_adjustment_does_not_see_the_menu(self):
        self.assertFalse(self._visible(self.basic_user))

    def test_user_with_adjustment_sees_the_menu(self):
        self.assertTrue(self._visible(self.adjust_user))
