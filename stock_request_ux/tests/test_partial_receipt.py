##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command
from odoo.tests import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPartialReceipt(TransactionCase):
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
        cls.product = cls.env["product.product"].create(
            {
                "name": "Product",
                "type": "consu",
                "is_storable": True,
                "route_ids": [Command.link(cls.route.id)],
            }
        )
        cls.env["stock.quant"]._update_available_quantity(cls.product, cls.source_loc, 100)
        cls.order = cls.env["stock.request.order"].create(
            {
                "warehouse_id": cls.warehouse.id,
                "location_id": cls.warehouse.lot_stock_id.id,
                "stock_request_ids": [
                    Command.create(
                        {
                            "product_id": cls.product.id,
                            "product_uom_id": cls.product.uom_id.id,
                            "product_uom_qty": 5.0,
                            "warehouse_id": cls.warehouse.id,
                            "location_id": cls.warehouse.lot_stock_id.id,
                            "route_id": cls.route.id,
                        }
                    )
                ],
            }
        )
        cls.request = cls.order.stock_request_ids

    def _validate(self, picking, qty, backorder):
        picking.move_ids.write({"quantity": qty, "picked": True})
        res = picking.button_validate()
        if isinstance(res, dict) and res.get("res_model") == "stock.backorder.confirmation":
            wizard = Form.from_action(self.env, res).save()
            if backorder:
                wizard.process()
            else:
                wizard.process_cancel_backorder()

    def test_backorder_keeps_the_request_open(self):
        self.order.action_confirm()
        picking = self.order.picking_ids
        self._validate(picking, 2.0, backorder=True)

        backorder = picking.backorder_ids
        self.assertEqual(len(backorder), 1)
        self.assertEqual(backorder.move_ids.stock_request_ids, self.request)
        self.assertIn(backorder, self.order.picking_ids)
        self.assertEqual(self.request.state, "open")
        self.assertEqual(self.request.qty_done, 2.0)
        self.assertEqual(self.request.qty_in_progress, 3.0)
        self.assertEqual(self.request.qty_cancelled, 0.0)

        self._validate(backorder, 3.0, backorder=True)
        self.assertEqual(self.request.state, "done")
        self.assertEqual(self.request.qty_done, 5.0)
        self.assertEqual(self.request.qty_cancelled, 0.0)

    def test_no_backorder_closes_the_request(self):
        self.order.action_confirm()
        self._validate(self.order.picking_ids, 2.0, backorder=False)

        self.assertEqual(self.request.state, "done")
        self.assertEqual(self.request.qty_done, 2.0)
        self.assertEqual(self.request.qty_cancelled, 3.0)
