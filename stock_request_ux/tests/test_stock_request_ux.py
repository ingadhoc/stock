from odoo import Command
from odoo.addons.base.tests.common import BaseCommon
from odoo.exceptions import AccessError


class TestStockRequestUx(BaseCommon):
    _test_user_groups = ("base.group_user", "stock.group_stock_manager", "stock_request.group_stock_request_manager")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env.ref("stock.warehouse0")
        cls.resupply_loc = cls.env["stock.location"].create(
            {
                "name": "Resupply",
                "usage": "internal",
                "location_id": cls.warehouse.view_location_id.id,
            }
        )
        cls.route = cls.env["stock.route"].create(
            {
                "name": "Transfer",
                "product_categ_selectable": False,
                "product_selectable": True,
                "sequence": 10,
            }
        )
        cls.env["stock.rule"].create(
            {
                "name": "Transfer",
                "route_id": cls.route.id,
                "location_src_id": cls.resupply_loc.id,
                "location_dest_id": cls.warehouse.lot_stock_id.id,
                "action": "pull",
                "picking_type_id": cls.warehouse.int_type_id.id,
                "procure_method": "make_to_stock",
                "warehouse_id": cls.warehouse.id,
            }
        )
        cls.transit_loc = cls.env["stock.location"].create(
            {
                "name": "Transit",
                "usage": "internal",
                "location_id": cls.warehouse.view_location_id.id,
            }
        )
        cls.route_two_steps = cls.env["stock.route"].create(
            {
                "name": "Transfer in two steps",
                "product_categ_selectable": False,
                "product_selectable": True,
                "sequence": 10,
            }
        )
        cls.env["stock.rule"].create(
            [
                {
                    "name": "Resupply to transit",
                    "route_id": cls.route_two_steps.id,
                    "location_src_id": cls.resupply_loc.id,
                    "location_dest_id": cls.transit_loc.id,
                    "action": "pull",
                    "location_dest_from_rule": True,
                    "picking_type_id": cls.warehouse.int_type_id.id,
                    "procure_method": "make_to_stock",
                    "warehouse_id": cls.warehouse.id,
                },
                {
                    "name": "Transit to stock",
                    "route_id": cls.route_two_steps.id,
                    "location_src_id": cls.transit_loc.id,
                    "location_dest_id": cls.warehouse.lot_stock_id.id,
                    "action": "pull",
                    "location_dest_from_rule": True,
                    "picking_type_id": cls.warehouse.int_type_id.id,
                    "procure_method": "make_to_order",
                    "warehouse_id": cls.warehouse.id,
                },
            ]
        )
        cls.env["ir.config_parameter"].sudo().set_str("stock.no_auto_scheduler", "True")
        cls.products = cls.env["product.product"]
        for code in ("A", "B", "C"):
            product = cls.env["product.product"].create(
                {
                    "name": f"Product {code}",
                    "default_code": code,
                    "type": "consu",
                    "is_storable": True,
                    "route_ids": [Command.set(cls.route.ids)],
                }
            )
            cls.env["stock.quant"].create(
                {"product_id": product.id, "location_id": cls.resupply_loc.id, "quantity": 20.0}
            )
            cls.products |= product
        cls.product_two_steps = cls.env["product.product"].create(
            {
                "name": "Product two steps",
                "type": "consu",
                "is_storable": True,
                "route_ids": [Command.set(cls.route_two_steps.ids)],
            }
        )
        cls.env["stock.quant"].create(
            {"product_id": cls.product_two_steps.id, "location_id": cls.resupply_loc.id, "quantity": 20.0}
        )

    def _create_order(self, product_qtys, user=None):
        """Order with one line per (product, quantity); lines of the same product share the moves."""
        return (
            self.env["stock.request.order"]
            .with_user(user or self.env.user)
            .create(
                {
                    "warehouse_id": self.warehouse.id,
                    "location_id": self.warehouse.lot_stock_id.id,
                    "stock_request_ids": [
                        Command.create(
                            {
                                "product_id": product.id,
                                "product_uom_id": product.uom_id.id,
                                "product_uom_qty": qty,
                                "warehouse_id": self.warehouse.id,
                                "location_id": self.warehouse.lot_stock_id.id,
                            }
                        )
                        for product, qty in product_qtys
                    ],
                }
            )
        )

    def test_order_goes_in_one_picking(self):
        """An order always leaves in a single picking, with the order as origin.

        Covers: all the lines of an order in one picking, picking origin is the
        order name, orders do not share pickings and the picking and its moves
        point back to the order.
        """
        order = self._create_order([(p, 5.0) for p in self.products])
        order.action_confirm()
        picking = order.picking_ids
        with self.subTest("the three lines of the order leave in one picking"):
            self.assertEqual(len(picking), 1)
            self.assertEqual(len(picking.move_ids), 3)
        with self.subTest("the origin of the picking is the order name"):
            self.assertEqual(picking.origin, order.name)
        with self.subTest("the picking and its moves point to the order"):
            self.assertEqual(picking.stock_request_order_ids, order)
            self.assertEqual(picking.stock_request_order_count, 1)
            self.assertEqual(picking.move_ids.mapped("request_order_id"), order)
        with self.subTest("another order does not reuse that picking"):
            other_order = self._create_order([(p, 5.0) for p in self.products])
            other_order.action_confirm()
            other_picking = other_order.picking_ids
            self.assertEqual(len(other_picking), 1)
            self.assertNotEqual(other_picking, picking)
            self.assertEqual(other_picking.origin, other_order.name)

    def test_cancel_remaining_partial(self):
        """Cancel remaining on a line delivered in part.

        Covers: the line keeps what was delivered, only the pending move is
        cancelled, the delivered move stays done, the line is closed and the
        order chatter records it.
        """
        order = self._create_order([(self.products[0], 5.0)])
        order.action_confirm()
        picking = order.picking_ids
        picking.action_assign()
        picking.move_ids.quantity = 2.0
        picking.move_ids.picked = True
        self.env["stock.backorder.confirmation"].with_context(button_validate_picking_ids=[picking.id]).create(
            {"pick_ids": [Command.link(picking.id)]}
        ).process()
        line = order.stock_request_ids
        done_move = picking.move_ids
        pending_move = picking.backorder_ids.move_ids
        with self.subTest("before cancelling, the line is open with a pending move"):
            self.assertTrue(pending_move)
            self.assertEqual(line.qty_done, 2.0)
            self.assertEqual(line.product_uom_qty, 5.0)
            self.assertNotIn(pending_move.state, ("done", "cancel"))

        line.button_cancel_remaining()
        line.invalidate_recordset()

        with self.subTest("the line keeps only what was delivered and is closed"):
            self.assertEqual(line.product_uom_qty, 2.0)
            self.assertEqual(line.state, "done")
        with self.subTest("only the pending move is cancelled"):
            self.assertEqual(pending_move.state, "cancel")
            self.assertEqual(done_move.state, "done")
        with self.subTest("the order chatter records the cancellation"):
            self.assertIn("Cancel remaining call", order.message_ids[0].body)

    def test_cancel_remaining_closes_in_one_click(self):
        """Cancel remaining closes the line on the first click after a return.

        Covers: nothing is pending to cancel, the line only has less delivered
        than requested, and a single click leaves it done with that quantity.
        """
        order = self._create_order([(self.products[0], 5.0)])
        order.action_confirm()
        picking = order.picking_ids
        picking.action_assign()
        picking.move_ids.quantity = 3.0
        picking.move_ids.picked = True
        self.env["stock.backorder.confirmation"].with_context(button_validate_picking_ids=[picking.id]).create(
            {"pick_ids": [Command.link(picking.id)]}
        ).process()
        returned = picking._create_return()
        returned.action_assign()
        returned.move_ids.product_uom_qty = 3.0
        returned.move_ids.quantity = 3.0
        returned.move_ids.picked = True
        returned._action_done()
        pending = picking.backorder_ids
        pending.action_assign()
        pending.move_ids.quantity = 2.0
        pending.move_ids.picked = True
        pending._action_done()
        line = order.stock_request_ids
        line.invalidate_recordset()
        with self.subTest("2 of 5 delivered and nothing pending: the line is still open"):
            self.assertEqual(line.qty_done, 2.0)
            self.assertEqual(line.qty_in_progress, 0.0)
            self.assertEqual(line.state, "open")

        line.button_cancel_remaining()

        with self.subTest("one click leaves the line with what was delivered and done"):
            self.assertEqual(line.product_uom_qty, 2.0)
            self.assertEqual(line.state, "done")

    def test_cancel_remaining_with_shared_move(self):
        """Cancel remaining on a line does not touch the other line of the same product.

        Covers: two lines of one product share a single move, a partial delivery,
        cancel remaining on one of them leaves the pending quantity of the other
        and it can still be delivered.
        """
        order = self._create_order([(self.products[0], qty) for qty in (3.0, 2.0)])
        order.action_confirm()
        line_3 = order.stock_request_ids.filtered(lambda r: r.product_uom_qty == 3.0)
        line_2 = order.stock_request_ids - line_3
        picking = order.picking_ids
        picking.action_assign()
        picking.move_ids.quantity = 2.0
        picking.move_ids.picked = True
        self.env["stock.backorder.confirmation"].with_context(button_validate_picking_ids=[picking.id]).create(
            {"pick_ids": [Command.link(picking.id)]}
        ).process()
        pending_move = picking.backorder_ids.move_ids
        with self.subTest("both lines wait for the same pending move"):
            self.assertEqual(len(pending_move), 1)
            self.assertEqual(pending_move.product_uom_qty, 3.0)
            self.assertEqual(pending_move.allocation_ids.stock_request_id, line_3 | line_2)

        line_2.button_cancel_remaining()
        (line_3 | line_2).invalidate_recordset()

        with self.subTest("the cancelled line has nothing left in progress"):
            self.assertEqual(line_2.qty_in_progress, 0.0)
            self.assertNotEqual(line_2.state, "open")
        with self.subTest("the other line keeps its pending quantity and stays open"):
            self.assertEqual(line_3.qty_in_progress, 1.0)
            self.assertEqual(line_3.state, "open")
        with self.subTest("the shared move only loses the quantity of the cancelled line"):
            self.assertEqual(pending_move.state, "assigned")
            self.assertEqual(pending_move.product_uom_qty, 1.0)

        pending = pending_move.picking_id
        pending.move_ids.quantity = 1.0
        pending.move_ids.picked = True
        pending._action_done()
        line_3.invalidate_recordset()
        with self.subTest("the other line is delivered in full afterwards"):
            self.assertEqual(line_3.qty_done, 3.0)
            self.assertEqual(line_3.state, "done")

    def test_cancel_remaining_with_shared_move_two_steps(self):
        """Cancel remaining on a line of a two step route does not touch the other line.

        Covers: the moves of both steps are shared, the cancelled line gives up
        what it has pending in each step and the other line still receives
        its quantity in the last step.
        """
        order = self._create_order([(self.product_two_steps, qty) for qty in (3.0, 2.0)])
        order.action_confirm()
        line_3 = order.stock_request_ids.filtered(lambda r: r.product_uom_qty == 3.0)
        line_2 = order.stock_request_ids - line_3
        first_step = order.picking_ids.filtered(lambda p: p.move_ids.location_id == self.resupply_loc)
        last_step = order.picking_ids.filtered(lambda p: p.move_ids.location_id == self.transit_loc)
        with self.subTest("both lines share the move of each step"):
            self.assertEqual(first_step.move_ids.product_uom_qty, 5.0)
            self.assertEqual(last_step.move_ids.product_uom_qty, 5.0)
            self.assertEqual(last_step.move_ids.allocation_ids.stock_request_id, line_3 | line_2)

        line_2.button_cancel_remaining()
        (line_3 | line_2).invalidate_recordset()

        with self.subTest("nothing delivered yet: each step only loses the quantity of the cancelled line"):
            self.assertEqual(first_step.move_ids.product_uom_qty, 3.0)
            self.assertEqual(last_step.move_ids.product_uom_qty, 3.0)
            self.assertNotIn(first_step.state, ("cancel", "done"))
            self.assertNotIn(last_step.state, ("cancel", "done"))
        with self.subTest("the other line keeps what is pending"):
            self.assertEqual(line_3.qty_in_progress, 3.0)
            self.assertEqual(line_3.state, "open")
            self.assertEqual(line_2.qty_in_progress, 0.0)

        first_step.action_assign()
        first_step.move_ids.quantity = 3.0
        first_step.move_ids.picked = True
        first_step._action_done()
        last_step.action_assign()
        last_step.move_ids.quantity = 3.0
        last_step.move_ids.picked = True
        last_step._action_done()
        line_3.invalidate_recordset()
        with self.subTest("the other line is delivered in full through the two steps"):
            self.assertEqual(line_3.qty_done, 3.0)
            self.assertEqual(line_3.state, "done")

    def test_cancel_remaining_keeps_return_in_progress(self):
        """Cancel remaining does not cancel a return that is still in progress.

        Covers: the return of what was delivered is waiting to be validated, the
        pending move is cancelled and the return keeps its quantity.
        """
        order = self._create_order([(self.products[0], 5.0)])
        order.action_confirm()
        picking = order.picking_ids
        picking.action_assign()
        picking.move_ids.quantity = 3.0
        picking.move_ids.picked = True
        self.env["stock.backorder.confirmation"].with_context(button_validate_picking_ids=[picking.id]).create(
            {"pick_ids": [Command.link(picking.id)]}
        ).process()
        pending_move = picking.backorder_ids.move_ids
        returned = picking._create_return()
        returned.move_ids.product_uom_qty = 1.0
        returned.action_assign()
        return_move = returned.move_ids
        line = order.stock_request_ids
        self.assertNotIn(return_move.state, ("done", "cancel"))

        line.button_cancel_remaining()

        with self.subTest("the pending move is cancelled"):
            self.assertEqual(pending_move.state, "cancel")
        with self.subTest("the return keeps its quantity and is not cancelled"):
            self.assertNotEqual(return_move.state, "cancel")
            self.assertNotEqual(returned.state, "cancel")
            self.assertEqual(return_move.product_uom_qty, 1.0)

    def test_cancel_remaining_shared_move_keeps_return_in_progress(self):
        """Cancel remaining with shared lines does not lower a return in progress.

        Covers: two lines of one product, 4 of 5 delivered and returned (return
        not validated yet), cancel remaining on the line that is still open.
        """
        order = self._create_order([(self.products[0], qty) for qty in (3.0, 2.0)])
        order.action_confirm()
        picking = order.picking_ids
        picking.action_assign()
        picking.move_ids.quantity = 4.0
        picking.move_ids.picked = True
        self.env["stock.backorder.confirmation"].with_context(button_validate_picking_ids=[picking.id]).create(
            {"pick_ids": [Command.link(picking.id)]}
        ).process()
        returned = picking._create_return()
        returned.move_ids.product_uom_qty = 4.0
        returned.action_assign()
        return_move = returned.move_ids
        open_line = order.stock_request_ids.filtered(lambda r: r.qty_in_progress > 0)
        self.assertEqual(len(open_line), 1)

        open_line.button_cancel_remaining()

        with self.subTest("the return keeps its quantity and is not cancelled"):
            self.assertNotEqual(return_move.state, "cancel")
            self.assertEqual(return_move.product_uom_qty, 4.0)

    def test_manual_copy_of_a_done_picking_is_not_counted(self):
        """A picking duplicated by hand does not add its quantity to the request line.

        Covers: the copy of a done move takes the allocation only when it is a
        return or a push, so what is delivered by the copy does not count twice.
        """
        order = self._create_order([(self.products[0], 5.0)])
        order.action_confirm()
        picking = order.picking_ids
        picking.picking_type_id.block_additional_quantity = False
        picking.action_assign()
        picking.move_ids.quantity = 5.0
        picking.move_ids.picked = True
        picking.button_validate()
        line = order.stock_request_ids
        self.assertEqual(line.qty_done, 5.0)

        copy = picking.copy()
        copy.action_confirm()
        copy.action_assign()
        copy.move_ids.quantity = 5.0
        copy.move_ids.picked = True
        copy.button_validate()
        line.invalidate_recordset()

        with self.subTest("the copy has no allocation"):
            self.assertFalse(copy.move_ids.allocation_ids)
        with self.subTest("the line counts only what the order delivered"):
            self.assertEqual(line.qty_done, 5.0)

    def test_manual_copy_of_an_open_picking_is_not_counted(self):
        """A picking duplicated by hand before it is done does not double the quantity in progress.

        Covers: only a split, a return or a push pass the allocation to the copy.
        """
        order = self._create_order([(self.products[0], 5.0)])
        order.action_confirm()
        picking = order.picking_ids
        picking.picking_type_id.block_additional_quantity = False
        line = order.stock_request_ids
        self.assertEqual(line.qty_in_progress, 5.0)

        copy = picking.copy()
        line.invalidate_recordset()

        with self.subTest("the copy has no allocation"):
            self.assertFalse(copy.move_ids.allocation_ids)
        with self.subTest("the line keeps the quantity in progress it had"):
            self.assertEqual(line.qty_in_progress, 5.0)

    def test_cancel_remaining_cancels_the_previous_steps_of_a_not_shared_move(self):
        """Cancel remaining in a two step route does not leave the first step waiting for nothing.

        Covers: after a partial delivery in both steps, the pending move of the
        first step only feeds the cancelled one, so it is cancelled too.
        """
        order = self._create_order([(self.product_two_steps, 5.0)])
        order.action_confirm()
        line = order.stock_request_ids
        first_step = order.picking_ids.filtered(lambda p: p.move_ids.location_id == self.resupply_loc)
        last_step = order.picking_ids - first_step
        for picking in (first_step, last_step):
            picking.action_assign()
            picking.move_ids.quantity = 2.0
            picking.move_ids.picked = True
            self.env["stock.backorder.confirmation"].with_context(button_validate_picking_ids=[picking.id]).create(
                {"pick_ids": [Command.link(picking.id)]}
            ).process()
        first_pending = first_step.backorder_ids.move_ids
        last_pending = last_step.backorder_ids.move_ids
        self.assertNotIn(first_pending.state, ("done", "cancel"))
        self.assertNotIn(last_pending.state, ("done", "cancel"))

        line.button_cancel_remaining()
        line.invalidate_recordset()

        with self.subTest("the pending move of the last step is cancelled"):
            self.assertEqual(last_pending.state, "cancel")
        with self.subTest("the pending move of the first step is cancelled too"):
            self.assertEqual(first_pending.state, "cancel")
        with self.subTest("the line is closed with what it delivered"):
            self.assertEqual(line.product_uom_qty, 2.0)
            self.assertEqual(line.state, "done")

    def test_cancel_remaining_by_a_request_user_without_inventory_access(self):
        """A user that can confirm an order can also cancel the remaining of a line.

        Covers: the stock moves are handled with sudo, as stock_request does when it cancels a line.
        """
        groups = self.env.ref("base.group_user") | self.env.ref("stock_request.group_stock_request_user")
        request_user = (
            self.env["res.users"]
            .sudo()
            .create(
                {
                    "name": "Request user",
                    "login": "request_user_cancel_remaining",
                    "group_ids": [Command.set(groups.ids)],
                }
            )
        )
        order = self._create_order([(self.products[0], 5.0)], user=request_user)
        order.action_confirm()
        picking = order.sudo().picking_ids
        picking.action_assign()
        picking.move_ids.quantity = 2.0
        picking.move_ids.picked = True
        self.env["stock.backorder.confirmation"].with_context(button_validate_picking_ids=[picking.id]).create(
            {"pick_ids": [Command.link(picking.id)]}
        ).process()
        line = order.stock_request_ids
        pending_move = picking.backorder_ids.move_ids

        line.with_user(request_user).button_cancel_remaining()
        line.invalidate_recordset()

        with self.subTest("the line is closed with what it delivered"):
            self.assertEqual(line.product_uom_qty, 2.0)
            self.assertEqual(line.state, "done")
        with self.subTest("the pending move is cancelled"):
            self.assertEqual(pending_move.state, "cancel")

    def test_cancel_remaining_of_a_line_that_the_user_cannot_modify(self):
        """The sudo of the button does not open the lines of another user.

        Covers: the user needs write access to the line, as the button only
        handles the stock moves with sudo.
        """
        groups = self.env.ref("base.group_user") | self.env.ref("stock_request.group_stock_request_user")
        users = (
            self.env["res.users"]
            .sudo()
            .create(
                [
                    {"name": name, "login": f"request_user_{name}", "group_ids": [Command.set(groups.ids)]}
                    for name in ("owner", "other")
                ]
            )
        )
        owner, other = users
        order = self._create_order([(self.products[0], 5.0)], user=owner)
        order.action_confirm()
        line = order.stock_request_ids

        with self.assertRaises(AccessError):
            line.with_user(other).button_cancel_remaining()
        line.invalidate_recordset()
        self.assertEqual(line.product_uom_qty, 5.0)
