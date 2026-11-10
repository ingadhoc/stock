##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from unittest.mock import patch

from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestReassignOnce(TransactionCase):
    """Confirming an order must release and reserve its picking once, not once per line.

    All the lines of an order share a single picking (see
    StockRequest._prepare_procurement_values), so reassigning line by line redid the whole
    picking as many times as lines it had: a 125 line order timed out at 300 s (ticket 132631).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
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
                "sequence": 10,
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
        cls.products = cls.env["product.product"].create(
            [
                {
                    "name": f"Product {index}",
                    "type": "consu",
                    "is_storable": True,
                    "route_ids": [Command.link(cls.route.id)],
                }
                for index in range(3)
            ]
        )
        for product in cls.products:
            cls.env["stock.quant"]._update_available_quantity(product, cls.source_loc, 100)
        cls.order = cls.env["stock.request.order"].create(
            {
                "warehouse_id": cls.warehouse.id,
                "location_id": cls.warehouse.lot_stock_id.id,
                "stock_request_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_uom_id": product.uom_id.id,
                            "product_uom_qty": 5.0,
                            "warehouse_id": cls.warehouse.id,
                            "location_id": cls.warehouse.lot_stock_id.id,
                            "route_id": cls.route.id,
                        }
                    )
                    for product in cls.products
                ],
            }
        )

    def test_reassign_runs_once_per_order(self):
        picking_model = type(self.env["stock.picking"])
        calls = []
        original = picking_model.do_unreserve

        def counting_do_unreserve(records, *args, **kwargs):
            calls.append(records)
            return original(records, *args, **kwargs)

        with patch.object(picking_model, "do_unreserve", counting_do_unreserve):
            self.order.action_confirm()

        self.assertEqual(len(self.order.stock_request_ids), 3)
        picking = self.order.picking_ids
        self.assertEqual(len(picking), 1, "The lines of an order are grouped into one picking")
        self.assertEqual(len(calls), 1, "The picking must be released once, not once per line")
        self.assertEqual(calls[0], picking)
        # The reservation the method exists for is still there.
        self.assertEqual(picking.state, "assigned")
        self.assertEqual(len(picking.move_ids), 3)
        self.assertTrue(all(move.state == "assigned" for move in picking.move_ids))
