from odoo import Command
from odoo.addons.base.tests.common import BaseCommon


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

    def _create_order(self, products, qty=5.0):
        return self.env["stock.request.order"].create(
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
                    for product in products
                ],
            }
        )

    def test_order_goes_in_one_picking(self):
        """An order always leaves in a single picking, with the order as origin.

        Covers: all the lines of an order in one picking, picking origin is the
        order name, orders do not share pickings and the picking and its moves
        point back to the order.
        """
        order = self._create_order(self.products)
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
            other_order = self._create_order(self.products)
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
        order = self._create_order(self.products[:1], qty=5.0)
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

    def test_return_after_partial_delivery(self):
        """A return subtracts what its delivery added to the line.

        Covers: the line goes back to what is really delivered, the pending
        move keeps its quantity and the line stays open.
        """
        order = self._create_order(self.products[:1], qty=5.0)
        order.action_confirm()
        picking = order.picking_ids
        picking.action_assign()
        picking.move_ids.quantity = 3.0
        picking.move_ids.picked = True
        self.env["stock.backorder.confirmation"].with_context(button_validate_picking_ids=[picking.id]).create(
            {"pick_ids": [Command.link(picking.id)]}
        ).process()
        line = order.stock_request_ids
        with self.subTest("after the partial delivery the line has 3 done and 2 in progress"):
            self.assertEqual(line.qty_done, 3.0)
            self.assertEqual(line.qty_in_progress, 2.0)

        returned = picking._create_return()
        returned.action_assign()
        returned.move_ids.product_uom_qty = 3.0
        returned.move_ids.quantity = 3.0
        returned.move_ids.picked = True
        returned._action_done()
        line.invalidate_recordset()

        with self.subTest("the return subtracts the delivered quantity"):
            self.assertEqual(line.qty_done, 0.0)
        with self.subTest("the pending move keeps its quantity and the line stays open"):
            self.assertEqual(line.qty_in_progress, 2.0)
            self.assertEqual(line.state, "open")

    def test_cancel_remaining_closes_in_one_click(self):
        """Cancel remaining closes the line on the first click after a return.

        Covers: nothing is pending to cancel, the line only has less delivered
        than requested, and a single click leaves it done with that quantity.
        """
        order = self._create_order(self.products[:1], qty=5.0)
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

    def test_cancel_remaining_closes_in_one_click_two_steps(self):
        """Cancel remaining closes the line on the first click in a two step route.

        Covers: the partial delivery is in the last step of the route and a
        single click leaves the line done with what was delivered.
        """
        order = self._create_order(self.product_two_steps, qty=5.0)
        order.action_confirm()
        first_step = order.picking_ids.filtered(lambda p: p.move_ids.location_id == self.resupply_loc)
        last_step = order.picking_ids.filtered(lambda p: p.move_ids.location_id == self.transit_loc)
        with self.subTest("the route has two steps"):
            self.assertEqual(len(first_step), 1)
            self.assertEqual(len(last_step), 1)
        first_step.action_assign()
        first_step.move_ids.quantity = 5.0
        first_step.move_ids.picked = True
        first_step._action_done()
        last_step.action_assign()
        last_step.move_ids.quantity = 2.0
        last_step.move_ids.picked = True
        self.env["stock.backorder.confirmation"].with_context(button_validate_picking_ids=[last_step.id]).create(
            {"pick_ids": [Command.link(last_step.id)]}
        ).process()
        line = order.stock_request_ids
        line.invalidate_recordset()
        with self.subTest("2 of 5 delivered in the last step and the line is still open"):
            self.assertEqual(line.qty_done, 2.0)
            self.assertEqual(line.state, "open")

        line.button_cancel_remaining()

        with self.subTest("one click leaves the line with what was delivered and done"):
            self.assertEqual(line.product_uom_qty, 2.0)
            self.assertEqual(line.state, "done")
