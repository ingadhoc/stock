from odoo import Command, fields
from odoo.addons.stock_landed_costs.tests.test_stockvaluationlayer import TestStockValuationLCCommon
from odoo.tests import Form, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestLandedCostEntries(TestStockValuationLCCommon):
    def _draft_lc(self, move, amount):
        lc = Form(self.env["stock.landed.cost"])
        lc.account_journal_id = self.stock_journal
        lc.picking_ids.add(move.picking_id)
        with lc.cost_lines.new() as cost_line:
            cost_line.product_id = self.productlc1
            cost_line.price_unit = amount
        lc = lc.save()
        lc.compute_landed_cost()
        return lc

    def test_landed_cost_entries_in_move_entries(self):
        """The entries of the validated landed costs join the move's journal entries,
        next to its vendor bill, and the main entry is still the bill."""
        move = self._make_in_move(self.product1, 4, unit_cost=200)
        order = move.purchase_line_id.order_id
        order.action_create_invoice()
        bill = order.invoice_ids
        bill.invoice_date = fields.Date.today()
        bill.action_post()
        self.assertEqual(move.all_account_move_ids, bill)

        lc_1 = self._make_lc(move, 400)
        lc_2 = self._make_lc(move, 100)
        self._draft_lc(move, 50)
        move.invalidate_recordset()

        expected = bill | lc_1.account_move_id | lc_2.account_move_id
        self.assertEqual(move.all_account_move_ids, expected)
        self.assertEqual(move.account_move_count, 3)
        self.assertEqual(move.related_account_move_id, bill)

        # Adjustment lines are restricted to stock managers.
        reader = new_test_user(
            self.env, "lc_entries_reader", groups="stock.group_stock_user,account.group_account_readonly"
        )
        self.assertEqual(set(move.with_user(reader).all_account_move_ids.ids), set(expected.ids))

    def test_landed_cost_entry_not_in_periodic_move(self):
        """On a receipt mixing perpetual and periodic products, the landed cost entry books
        only the perpetual one, so only its move lists it."""
        periodic_categ = self.stock_account_product_categ.copy({"property_valuation": "periodic"})
        periodic_product = self.env["product.product"].create(
            {"name": "periodic product", "is_storable": True, "categ_id": periodic_categ.id}
        )
        order = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "order_line": [
                    Command.create({"product_id": product.id, "product_qty": 2, "price_unit": 100})
                    for product in self.product1 | periodic_product
                ],
            }
        )
        order.button_confirm()
        receipt = order.picking_ids
        receipt.move_ids.quantity = 2
        receipt.button_validate()
        perpetual_move = receipt.move_ids.filtered(lambda move: move.product_id == self.product1)
        periodic_move = receipt.move_ids - perpetual_move

        lc = self._make_lc(perpetual_move, 100)
        self.assertTrue(lc.account_move_id)
        receipt.move_ids.invalidate_recordset()

        self.assertIn(lc.account_move_id, perpetual_move.all_account_move_ids)
        self.assertNotIn(lc.account_move_id, periodic_move.all_account_move_ids)
