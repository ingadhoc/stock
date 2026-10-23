##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from unittest.mock import patch

from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestOrderpointReviewed(TransactionCase):
    """Reviewed follows the quantity to order entered by hand, not every recompute of it."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.view = cls.env.ref("stock.view_warehouse_orderpoint_tree_editable")
        cls.warehouse = cls.env.ref("stock.warehouse0")
        cls.product = cls.env["product.product"].create({"name": "Reviewed Product", "is_storable": True})
        cls.Orderpoint = cls.env["stock.warehouse.orderpoint"].with_context(
            default_location_id=cls.warehouse.lot_stock_id.id
        )

    def _new_rule(self):
        with Form(self.Orderpoint, view=self.view) as form:
            form.product_id = self.product
            form.trigger = "manual"
            form.product_min_qty = 5
            form.product_max_qty = 10
        return form.record

    def test_new_rule_is_not_reviewed(self):
        self.assertFalse(self._new_rule().reviewed)

    def test_editing_min_does_not_review(self):
        rule = self._new_rule()
        with Form(rule, view=self.view) as form:
            form.product_min_qty = 8
        self.assertFalse(rule.reviewed)

    def test_quantity_entered_by_hand_reviews(self):
        rule = self._new_rule()
        with Form(rule, view=self.view) as form:
            form.qty_to_order = 3
        self.assertTrue(rule.reviewed)

    def test_mass_edit_reviews(self):
        rule = self._new_rule()
        rule.reviewed = False
        rule.write({"qty_to_order": 4})
        self.assertTrue(rule.reviewed)

    def test_undo_keeps_reviewed(self):
        rule = self._new_rule()
        rule.write({"qty_to_order": 4})
        rule.action_remove_manual_qty_to_order()
        self.assertTrue(rule.reviewed)

    def test_ordering_clears_reviewed(self):
        """super() writes the quantity to order, so the clear has to come after it."""
        rule = self._new_rule()
        rule.write({"qty_to_order": 4})
        with patch.object(type(rule), "_procure_orderpoint_confirm"):
            rule.action_replenish()
        self.assertFalse(rule.reviewed)
