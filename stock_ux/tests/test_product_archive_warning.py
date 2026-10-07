##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProductArchiveWarning(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stock_loc = (
            cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1).lot_stock_id
        )
        cls.customer_loc = cls.env.ref("stock.stock_location_customers")
        cls.product = cls.env["product.product"].create({"name": "Archive Test", "is_storable": True})

    def _move(self, state):
        move = self.env["stock.move"].create(
            {
                "product_id": self.product.id,
                "product_uom_qty": 1,
                "location_id": self.stock_loc.id,
                "location_dest_id": self.customer_loc.id,
            }
        )
        move.state = state
        return move

    def _warning(self, res):
        self.assertFalse(self.product.active)
        return res.get("params", {}).get("message", "") if res else ""

    def test_stock_warns_and_archives(self):
        self.env["stock.quant"]._update_available_quantity(self.product, self.stock_loc, 3)
        message = self._warning(self.product.action_archive())
        self.assertIn("internal or transit", message)
        self.assertNotIn("pending inventory moves", message)

    def test_pending_moves_warn_from_template(self):
        self._move("confirmed")
        message = self._warning(self.product.product_tmpl_id.action_archive())
        self.assertIn("pending inventory moves", message)
        self.assertNotIn("internal or transit", message)

    def test_done_or_cancelled_moves_do_not_warn(self):
        self._move("done")
        self._move("cancel")
        self.assertFalse(self._warning(self.product.action_archive()))
