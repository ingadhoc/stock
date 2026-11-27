##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import importlib.util
from pathlib import Path

from odoo import Command
from odoo.tests import Form, TransactionCase, tagged

MIGRATION = Path(__file__).parents[1] / "migrations" / "19.0.1.2.0" / "post-migration.py"


def load_migration():
    spec = importlib.util.spec_from_file_location("stock_request_ux_post_migration_19_0_1_2_0", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@tagged("post_install", "-at_install")
class TestMigrationBackorder(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.migration = load_migration()
        cls.warehouse = cls.env.ref("stock.warehouse0")
        cls.source_loc = cls.env["stock.location"].create(
            {
                "name": "Resupply",
                "usage": "internal",
                "location_id": cls.warehouse.view_location_id.id,
            }
        )
        cls.route = cls.env["stock.route"].create(
            {
                "name": "Resupply transfer",
                "product_selectable": True,
                "rule_ids": [
                    Command.create(
                        {
                            "name": "Resupply transfer",
                            "action": "pull",
                            "location_src_id": cls.source_loc.id,
                            "location_dest_id": cls.warehouse.lot_stock_id.id,
                            "picking_type_id": cls.warehouse.int_type_id.id,
                            "procure_method": "make_to_stock",
                            "warehouse_id": cls.warehouse.id,
                        }
                    )
                ],
            }
        )
        cls.product = cls.env["product.product"].create({"name": "Product", "type": "consu", "is_storable": True})
        cls.env["stock.quant"]._update_available_quantity(cls.product, cls.source_loc, 100)

    def _request(self, product, qty):
        order = self.env["stock.request.order"].create(
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
                            "route_id": self.route.id,
                        }
                    )
                ],
            }
        )
        order.action_confirm()
        return order.stock_request_ids

    def _receive_part(self, picking, qty):
        picking.move_ids.write({"quantity": qty, "picked": True})
        Form.from_action(self.env, picking.button_validate()).save().process()
        return picking.backorder_ids

    def _break_like_before(self, request, picking, backorder):
        """Leave the data as the copy_data patch left it: the backorder move without allocation,
        the source allocation with all it asked for, and the request closed."""
        for move in backorder.move_ids:
            source = picking.move_ids.filtered(lambda m, mv=move: m.product_id == mv.product_id).allocation_ids
            source.requested_product_uom_qty += move.allocation_ids.requested_product_uom_qty
            move.allocation_ids.unlink()
        request.check_done()
        self.env.flush_all()

    def test_backorder_linked_and_request_reopened(self):
        request = self._request(self.product, 5)
        picking = request.picking_ids
        backorder = self._receive_part(picking, 2)
        self._break_like_before(request, picking, backorder)
        self.assertEqual(request.state, "done")
        self.assertEqual(request.qty_cancelled, 3)

        self.migration.migrate(self.env.cr, "19.0.1.1.1")

        self.assertEqual(backorder.move_ids.allocation_ids.stock_request_id, request)
        self.assertEqual(backorder.move_ids.allocation_ids.requested_product_uom_qty, 3)
        self.assertEqual(picking.move_ids.allocation_ids.requested_product_uom_qty, 2)
        self.assertEqual(request.state, "open")
        self.assertEqual((request.qty_done, request.qty_in_progress, request.qty_cancelled), (2, 3, 0))

        backorder.move_ids.write({"quantity": 3, "picked": True})
        backorder.button_validate()
        self.assertEqual(request.state, "done")
        self.assertEqual(request.qty_done, 5)

    def test_backorder_chain_linked(self):
        request = self._request(self.product, 5)
        picking = request.picking_ids
        backorder = self._receive_part(picking, 2)
        self._break_like_before(request, picking, backorder)
        # With the patch the backorder of the backorder had no allocation either
        backorder_2 = self._receive_part(backorder, 1)
        self.assertFalse(backorder_2.move_ids.allocation_ids)
        self.env.flush_all()

        self.migration.migrate(self.env.cr, "19.0.1.1.1")

        allocs = (picking | backorder | backorder_2).move_ids.allocation_ids
        self.assertEqual(allocs.stock_request_id, request)
        self.assertEqual(
            [(a.requested_product_uom_qty, a.allocated_product_qty) for a in allocs.sorted("stock_move_id")],
            [(2, 2), (1, 1), (2, 0)],
        )
        self.assertEqual(request.state, "open")
        self.assertEqual((request.qty_done, request.qty_in_progress, request.qty_cancelled), (3, 2, 0))

        backorder_2.move_ids.write({"quantity": 2, "picked": True})
        backorder_2.button_validate()
        self.assertEqual(request.state, "done")
        self.assertEqual(request.qty_done, 5)

    def test_same_product_twice_left_alone(self):
        request = self._request(self.product, 5)
        request.copy({"order_id": request.order_id.id})
        picking = request.picking_ids
        backorder = self._receive_part(picking, 2)
        self._break_like_before(request, picking, backorder)

        self.migration.migrate(self.env.cr, "19.0.1.1.1")

        self.assertFalse(backorder.move_ids.allocation_ids)

    def test_trimmed_kit_allocation_restored(self):
        if "bom_line_id" not in self.env["stock.move"]._fields:
            self.skipTest("mrp is not installed")
        can = self.env["product.product"].create({"name": "Can", "type": "consu", "is_storable": True})
        pack = self.env["product.product"].create({"name": "Pack of 12", "type": "consu", "is_storable": True})
        self.env["stock.quant"]._update_available_quantity(can, self.source_loc, 500)
        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": pack.product_tmpl_id.id,
                "type": "phantom",
                "product_qty": 1.0,
                "bom_line_ids": [Command.create({"product_id": can.id, "product_qty": 12})],
            }
        )
        request = self._request(pack, 8)
        alloc = request.allocation_ids
        self.assertEqual(alloc.requested_product_uom_qty, 96)
        # What the migration of stock_request 19.0.1.1.0 left: the kits instead of the cans
        alloc.requested_product_uom_qty = 8
        self.env.flush_all()

        self.migration.migrate(self.env.cr, "19.0.1.1.1")

        self.assertEqual(alloc.requested_product_uom_qty, 96)

    def test_kit_state_left_to_stock_request_mrp(self):
        if "bom_line_id" not in self.env["stock.move"]._fields:
            self.skipTest("mrp is not installed")
        self.env["ir.module.module"].search([("name", "=", "stock_request_mrp")]).state = "uninstalled"
        can = self.env["product.product"].create({"name": "Can", "type": "consu", "is_storable": True})
        pack = self.env["product.product"].create({"name": "Pack of 12", "type": "consu", "is_storable": True})
        self.env["stock.quant"]._update_available_quantity(can, self.source_loc, 500)
        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": pack.product_tmpl_id.id,
                "type": "phantom",
                "product_qty": 1.0,
                "bom_line_ids": [Command.create({"product_id": can.id, "product_qty": 12})],
            }
        )
        request = self._request(pack, 8)
        request.allocation_ids.requested_product_uom_qty = 8
        request.action_done()
        self.env.flush_all()

        self.migration.migrate(self.env.cr, "19.0.1.1.1")

        self.assertEqual(request.allocation_ids.requested_product_uom_qty, 96)
        self.assertEqual(request.state, "done")
