from datetime import timedelta

from odoo import Command
from odoo.tests import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMergeNegativeMoves(TransactionCase):
    """Lowering a line quantity must cancel what is pending, never create a return.

    Covers the pass that absorbs what core left of the negative move into pending moves of
    the same demand: demand split across open transfers, pending moves that drifted from the
    negative mirror, pull chains, the order in which transfers are reduced, and what must be
    left alone.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if "exception.rule" in cls.env:
            cls.env["exception.rule"].search([]).write({"active": False})
        cls.customers = cls.env.ref("stock.stock_location_customers")
        cls.partner = cls.env["res.partner"].create({"name": "Customer"})
        cls.product = cls.env["product.product"].create({"name": "Storable", "type": "consu", "is_storable": True})
        cls.wh1, cls.wh2, cls.wh3, cls.whm, cls.whn = (
            cls.env["stock.warehouse"].create({"name": f"WH {code}", "code": code, "delivery_steps": steps})
            for code, steps in (
                ("T1S", "ship_only"),
                ("T2S", "pick_ship"),
                ("T3S", "pick_pack_ship"),
                ("TMS", "pick_ship"),
                ("TNS", "pick_ship"),
            )
        )
        # Output zone kept under the stock location, as some warehouses are set up.
        cls.whn.wh_output_stock_loc_id.location_id = cls.whn.lot_stock_id
        for wh in (cls.wh1, cls.wh2, cls.wh3, cls.whm, cls.whn):
            cls.env["stock.quant"]._update_available_quantity(cls.product, wh.lot_stock_id, 100)
        # Pre-18 chained pull rules, created together: only the first leg is make to stock.
        cls.mto_route = cls.env["stock.route"].create(
            {
                "name": "Legacy pick + ship",
                "sale_selectable": True,
                "rule_ids": [
                    Command.create(
                        {
                            "name": name,
                            "action": "pull",
                            "location_src_id": src.id,
                            "location_dest_id": dest.id,
                            "picking_type_id": ptype.id,
                            "procure_method": method,
                            "warehouse_id": cls.whm.id,
                        }
                    )
                    for name, src, dest, ptype, method in (
                        (
                            "Pick",
                            cls.whm.lot_stock_id,
                            cls.whm.wh_output_stock_loc_id,
                            cls.whm.pick_type_id,
                            "make_to_stock",
                        ),
                        ("Ship", cls.whm.wh_output_stock_loc_id, cls.customers, cls.whm.out_type_id, "make_to_order"),
                    )
                ],
            }
        )

    def _order(self, warehouse, *qtys, route=None, product=None, uom=None):
        product = product or self.product
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": warehouse.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_uom_qty": qty,
                            "product_uom": (uom or product.uom_id).id,
                            "route_id": route.id if route else False,
                        }
                    )
                    for qty in qtys
                ],
            }
        )
        order.action_confirm()
        return order

    def _open(self, order, picking_type):
        return order.picking_ids.filtered(
            lambda p: p.picking_type_id == picking_type and p.state not in ("done", "cancel")
        ).sorted("id")

    def _validate(self, pickings, qty=None):
        for move in pickings.move_ids:
            move.quantity = move.product_uom_qty if qty is None else qty
            move.picked = True
        res = pickings.button_validate()
        if isinstance(res, dict) and res.get("res_model") == "stock.backorder.confirmation":
            Form(self.env["stock.backorder.confirmation"].with_context(**res["context"])).save().process()

    def _assert_nothing_left(self, order, put_back=0):
        """No move from the customer and nothing left to deliver; only goods already moved
        to an intermediate location go back to stock."""
        pending = self.env["stock.move"].search(
            [("group_id", "=", order.procurement_group_id.id), ("state", "not in", ("done", "cancel"))]
        )
        self.assertFalse(
            pending.filtered(lambda m: m.location_id.usage == "customer"), "a return from the customer was created"
        )
        forward = pending.filtered(lambda m: m.location_dest_id != order.warehouse_id.lot_stock_id)
        self.assertFalse(forward, "something is still pending for a cancelled quantity")
        self.assertEqual(sum(pending.mapped("product_uom_qty")), put_back, "put-back to stock")

    def test_split_demand_is_netted_on_every_route(self):
        """Given the pending demand of a leg split in two open transfers (the first one printed
        before the quantity was raised), when the line goes down to zero, then both transfers
        are cancelled and no return is created; goods already moved to an intermediate location
        go back to stock."""
        cases = [
            ("1 step", self.wh1, None, "out", False, 0),
            ("2 steps push, pick split", self.wh2, None, "pick", False, 0),
            ("2 steps push, pick done, ship split", self.wh2, None, "out", True, 6),
            ("3 steps push, pick done, pack split", self.wh3, None, "pack", True, 6),
            ("2 steps legacy pull, pick split", self.whm, self.mto_route, "pick", False, 0),
            ("2 steps, output inside stock, pick done, ship split", self.whn, None, "out", True, 6),
        ]
        for label, wh, route, split_leg, first_leg_done, put_back in cases:
            with self.subTest(label):
                leg = {"pick": wh.pick_type_id, "pack": wh.pack_type_id, "out": wh.out_type_id}[split_leg]
                order = self._order(wh, 4, route=route)
                if first_leg_done:
                    self._validate(self._open(order, wh.pick_type_id))
                self._open(order, leg).do_print_picking()
                order.order_line.product_uom_qty = 6
                if first_leg_done:
                    self._validate(self._open(order, wh.pick_type_id))
                self.assertEqual(len(self._open(order, leg)), 2, "raising the quantity should split the leg")
                order.order_line.product_uom_qty = 0
                self._assert_nothing_left(order, put_back)

    def test_pull_chains_keep_their_links(self):
        """Given a legacy pull chain whose pick leg is split or was moved, or whose line lost the
        old route, when the line goes down, then the chain of that line is reduced consistently
        and a pick serving another line is left alone."""
        with self.subTest("pick partially done, printed backorder"):
            order = self._order(self.whm, 4, route=self.mto_route)
            self._validate(self._open(order, self.whm.pick_type_id), qty=2)
            self._open(order, self.whm.pick_type_id).do_print_picking()
            order.order_line.product_uom_qty = 0
            self._assert_nothing_left(order, put_back=2)
        with self.subTest("pick destination moved to a sub-location of the output"):
            bay = self.env["stock.location"].create({"name": "Bay", "location_id": self.whm.wh_output_stock_loc_id.id})
            order = self._order(self.whm, 6, route=self.mto_route)
            self._open(order, self.whm.pick_type_id).location_dest_id = bay
            order.order_line.product_uom_qty = 2
            chain = order.order_line.move_ids | order.order_line.move_ids.move_orig_ids
            pending = chain.filtered(lambda m: m.state not in ("done", "cancel"))
            self.assertFalse(
                pending.filtered(lambda m: m.location_id.usage == "customer"), "a return from the customer was created"
            )
            self.assertEqual(
                sorted(pending.mapped("product_uom_qty")), [2, 2], "pick and ship should both go down to 2"
            )
        with self.subTest("old pull chain after the line route was removed"):
            order = self._order(self.whm, 10, route=self.mto_route)
            (order.order_line.move_ids | order.order_line.move_ids.move_orig_ids).location_final_id = False
            order.order_line.route_id = False
            order.order_line.product_uom_qty = 6
            ship = order.order_line.move_ids.filtered(
                lambda m: m.location_dest_id == self.customers and m.state != "cancel"
            )
            self.assertEqual(ship.mapped("product_uom_qty"), [6], "the ship leg of the old chain should go down to 6")
            self.assertFalse(order.picking_ids.filtered(lambda p: p.location_id == self.customers))
        with self.subTest("another line of the same product"):
            order = self._order(self.whm, 4, route=self.mto_route)
            self._open(order, self.whm.pick_type_id).do_print_picking()
            order.write(
                {
                    "order_line": [
                        Command.create(
                            {"product_id": self.product.id, "product_uom_qty": 3, "route_id": self.mto_route.id}
                        )
                    ]
                }
            )
            second_pick = self._open(order, self.whm.pick_type_id).filtered(lambda p: not p.printed)
            second_pick.do_print_picking()
            order.order_line[0].product_uom_qty = 0
            self.assertEqual(second_pick.move_ids.product_uom_qty, 3, "the pick of the other line was reduced")
            self.assertEqual(second_pick.move_ids.move_dest_ids.sale_line_id, order.order_line[1])
            self.assertFalse(order.picking_ids.filtered(lambda p: p.location_id == self.customers))

    def test_least_advanced_transfers_are_reduced_first(self):
        """Given several open transfers for the same line, when the line goes down, then the
        least advanced ones are reduced first (not printed, not reserved, newest), a reduced
        transfer keeps its reservation, and a unit finer than the line's does not fail."""
        with self.subTest("three deliveries, two printed"):
            order = self._order(self.wh1, 4)
            self._open(order, self.wh1.out_type_id).do_print_picking()
            order.order_line.product_uom_qty = 6
            self._open(order, self.wh1.out_type_id)[-1].do_print_picking()
            order.order_line.product_uom_qty = 8
            oldest, newest_printed, unprinted = self._open(order, self.wh1.out_type_id)
            order.order_line.product_uom_qty = 3
            self.assertEqual(self._open(order, self.wh1.out_type_id), oldest)
            self.assertEqual(oldest.move_ids.product_uom_qty, 3)
            self.assertEqual((newest_printed | unprinted).mapped("state"), ["cancel", "cancel"])
            self.assertFalse(order.picking_ids.filtered(lambda p: p.location_id == self.customers))
        with self.subTest("an unreserved delivery before a reserved one"):
            scarce = self.env["product.product"].create({"name": "Scarce", "type": "consu", "is_storable": True})
            order = self._order(self.wh1, 4, product=scarce)
            unreserved = self._open(order, self.wh1.out_type_id)
            unreserved.do_print_picking()
            self.env["stock.quant"]._update_available_quantity(scarce, self.wh1.lot_stock_id, 10)
            order.order_line.product_uom_qty = 6
            reserved = self._open(order, self.wh1.out_type_id) - unreserved
            reserved.do_print_picking()
            self.assertEqual((unreserved.state, reserved.state), ("confirmed", "assigned"))
            order.order_line.product_uom_qty = 5
            self.assertEqual(unreserved.move_ids.product_uom_qty, 3)
            self.assertEqual(reserved.move_ids.product_uom_qty, 2)
        with self.subTest("a reduced delivery keeps its reservation"):
            wh = self.env["stock.warehouse"].create({"name": "WH manual", "code": "TMR", "delivery_steps": "ship_only"})
            wh.out_type_id.reservation_method = "manual"
            self.env["stock.quant"]._update_available_quantity(self.product, wh.lot_stock_id, 10)
            order = self._order(wh, 4)
            printed = self._open(order, wh.out_type_id)
            printed.action_assign()
            printed.do_print_picking()
            order.order_line.product_uom_qty = 6
            order.order_line.product_uom_qty = 3
            self.assertEqual((printed.move_ids.product_uom_qty, printed.move_ids.quantity), (3, 3))
        with self.subTest("units finer than the line unit of measure"):
            self.env["ir.config_parameter"].sudo().set_param("stock.propagate_uom", "1")
            self.env.ref("uom.product_uom_unit").rounding = 1.0
            order = self._order(self.wh1, 1, uom=self.env.ref("uom.product_uom_dozen"))
            self._open(order, self.wh1.out_type_id).do_print_picking()
            order.order_line.product_uom_qty = 2
            self._open(order, self.wh1.out_type_id)[-1].do_print_picking()
            order.order_line.product_uom_qty = 0.96

    def test_drifted_pending_moves_are_still_netted(self):
        """Given a pending move that no longer matches the negative mirror exactly (deadline or
        date, empty final location, source or destination moved, another operation type chosen
        by a conditional push rule, delivery address or delivery steps changed after
        confirming), when the line goes down to zero, then it is still cancelled and no return
        is created."""
        with self.subTest("deadline moved"):
            order = self._order(self.wh1, 4)
            for move in order.order_line.move_ids:
                move.date_deadline += timedelta(minutes=10)
            order.order_line.product_uom_qty = 0
            self._assert_nothing_left(order)
        with self.subTest("date moved while merging only moves of the same date"):
            self.env["ir.config_parameter"].sudo().set_param("stock.merge_only_same_date", "True")
            order = self._order(self.wh1, 4)
            for move in order.order_line.move_ids:
                move.date += timedelta(days=1)
            order.order_line.product_uom_qty = 0
            self._assert_nothing_left(order)
            self.env["ir.config_parameter"].sudo().set_param("stock.merge_only_same_date", False)
        with self.subTest("empty final location, as in migrated databases"):
            order = self._order(self.wh1, 4)
            order.order_line.move_ids.location_final_id = False
            order.order_line.product_uom_qty = 0
            self._assert_nothing_left(order)
        with self.subTest("delivery reserved from a sub-location"):
            shelf = self.env["stock.location"].create({"name": "Shelf", "location_id": self.wh1.lot_stock_id.id})
            self.env["stock.quant"]._update_available_quantity(self.product, shelf, 10)
            order = self._order(self.wh1, 4)
            self._open(order, self.wh1.out_type_id).location_id = shelf
            order.order_line.product_uom_qty = 0
            self._assert_nothing_left(order)
        with self.subTest("delivery source moved to another warehouse"):
            order = self._order(self.wh1, 4)
            self._open(order, self.wh1.out_type_id).location_id = self.wh2.lot_stock_id
            order.order_line.product_uom_qty = 0
            self._assert_nothing_left(order)
        with self.subTest("delivery destination moved to a customer sub-location"):
            branch = self.env["stock.location"].create(
                {"name": "Branch", "usage": "customer", "location_id": self.customers.id}
            )
            order = self._order(self.wh1, 4)
            delivery = self._open(order, self.wh1.out_type_id)
            delivery.location_dest_id = branch
            delivery.move_ids.location_final_id = branch
            order.order_line.product_uom_qty = 0
            self._assert_nothing_left(order)
        with self.subTest("delivery address with its own customer location"):
            depot = self.env["stock.location"].create(
                {"name": "Depot", "usage": "customer", "location_id": self.customers.id}
            )
            address = self.env["res.partner"].create(
                {
                    "name": "Depot address",
                    "parent_id": self.partner.id,
                    "type": "delivery",
                    "property_stock_customer": depot.id,
                }
            )
            order = self._order(self.wh1, 4)
            self._open(order, self.wh1.out_type_id).do_print_picking()
            order.order_line.product_uom_qty = 6
            order.partner_shipping_id = address
            order.order_line.product_uom_qty = 0
            self._assert_nothing_left(order)
        with self.subTest("ship leg routed through another operation type"):
            wh = self.env["stock.warehouse"].create(
                {"name": "WH conditional", "code": "TDS", "delivery_steps": "pick_ship"}
            )
            self.env["stock.quant"]._update_available_quantity(self.product, wh.lot_stock_id, 10)
            pickup = self.env["stock.picking.type"].create(
                {
                    "name": "Customer pickup",
                    "code": "outgoing",
                    "sequence_code": "PKP",
                    "warehouse_id": wh.id,
                    "default_location_src_id": wh.wh_output_stock_loc_id.id,
                    "default_location_dest_id": self.customers.id,
                }
            )
            push = wh.delivery_route_id.rule_ids.filtered(lambda r: r.action == "push")
            push.copy(
                {
                    "picking_type_id": pickup.id,
                    "push_domain": "[('move_line_ids', '!=', False)]",
                    "sequence": push.sequence - 1,
                }
            )
            order = self._order(wh, 4)
            self._validate(self._open(order, wh.pick_type_id))
            self.assertTrue(self._open(order, pickup), "the ship leg should use the conditional rule")
            order.order_line.product_uom_qty = 0
            self._assert_nothing_left(order, put_back=4)
        for label, steps_before, steps_after in (
            ("warehouse moved from 1 to 2 steps after confirming", "ship_only", "pick_ship"),
            ("warehouse moved from 2 steps to 1 after confirming", "pick_ship", "ship_only"),
        ):
            with self.subTest(label):
                wh = self.env["stock.warehouse"].create(
                    {
                        "name": label,
                        "code": "TR" + steps_before[:1].upper() + steps_after[:1].upper(),
                        "delivery_steps": steps_before,
                    }
                )
                self.env["stock.quant"]._update_available_quantity(self.product, wh.lot_stock_id, 10)
                order = self._order(wh, 4)
                wh.delivery_steps = steps_after
                order.order_line.product_uom_qty = 0
                self._assert_nothing_left(order)

    def test_drifted_purchase_receipts_are_still_netted(self):
        """Given a purchase whose pending receipt drifted from the negative mirror (destination
        moved to a sub-location, empty final location), when the line goes down to what was
        received, then the receipt is cancelled and nothing goes back to the vendor."""
        if self.env["ir.module.module"]._get("purchase_stock").state != "installed":
            self.skipTest("purchase_stock is not installed")
        vendor = self.env["res.partner"].create({"name": "Vendor"})
        shelf = self.env["stock.location"].create({"name": "Receipt shelf", "location_id": self.wh1.lot_stock_id.id})
        drifts = (
            ("receipt moved to a sub-location", lambda receipt: receipt.write({"location_dest_id": shelf.id})),
            (
                "empty final location, as in migrated databases",
                lambda receipt: receipt.move_ids.write({"location_final_id": False}),
            ),
        )
        for label, drift in drifts:
            with self.subTest(label):
                order = self.env["purchase.order"].create(
                    {
                        "partner_id": vendor.id,
                        "picking_type_id": self.wh1.in_type_id.id,
                        "order_line": [
                            Command.create({"product_id": self.product.id, "product_qty": 10, "price_unit": 5})
                        ],
                    }
                )
                order.button_confirm()
                self._validate(order.picking_ids, qty=4)
                drift(order.picking_ids.filtered(lambda p: p.state not in ("done", "cancel")))
                order.order_line.product_qty = 4
                pending = order.order_line.move_ids.filtered(lambda m: m.state not in ("done", "cancel"))
                self.assertFalse(pending, "something is still pending or a return to the vendor was created")

    def test_other_lines_destinations_and_prepared_moves_are_left_alone(self):
        """Given pending moves of another line of the same product, with another final
        destination, or already prepared by the warehouse, when a line goes down, then those
        moves are not reduced."""
        with self.subTest("another line of the same product"):
            order = self._order(self.wh1, 4, 3)
            self._open(order, self.wh1.out_type_id).do_print_picking()
            order.order_line[0].product_uom_qty = 6
            order.order_line[0].product_uom_qty = 0
            first, second = order.order_line
            self.assertFalse(first.move_ids.filtered(lambda m: m.state != "cancel"))
            self.assertEqual(second.move_ids.filtered(lambda m: m.state != "cancel").mapped("product_uom_qty"), [3])
        with self.subTest("another final destination"):
            other_customers = self.env["stock.location"].create(
                {"name": "Other customers", "usage": "customer", "location_id": self.customers.location_id.id}
            )
            order = self._order(self.wh2, 4)
            pick = self._open(order, self.wh2.pick_type_id)
            pick.move_ids.location_final_id = other_customers
            order.order_line.product_uom_qty = 0
            self.assertEqual(pick.move_ids.product_uom_qty, 4, "a move headed to another final destination was reduced")
        with self.subTest("a delivery already prepared"):
            order = self._order(self.wh1, 4)
            prepared = self._open(order, self.wh1.out_type_id)
            prepared.do_print_picking()
            prepared.move_ids.picked = True
            order.order_line.product_uom_qty = 6
            order.order_line.product_uom_qty = 0
            self.assertEqual((prepared.move_ids.product_uom_qty, prepared.move_ids.quantity), (4, 4))
