from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOrderpointQtyToOrderUpdate(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.wh1 = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.wh2 = cls.env["stock.warehouse"].create({"name": "Orderpoint WH2", "code": "OPWH2"})
        cls.supplier_location = cls.env.ref("stock.stock_location_suppliers")
        cls.product = cls.env["product.product"].create({"name": "Orderpoint Update Product", "is_storable": True})
        cls.orderpoint_wh1, cls.orderpoint_wh2 = cls.env["stock.warehouse.orderpoint"].create(
            [
                {
                    "product_id": cls.product.id,
                    "location_id": wh.lot_stock_id.id,
                    "product_min_qty": 10,
                    "product_max_qty": 10,
                    "trigger": "manual",
                }
                for wh in (cls.wh1, cls.wh2)
            ]
        )

    def _receipt(self, qty, validate=True):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.wh1.in_type_id.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.wh1.lot_stock_id.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "name": self.product.name,
                            "product_id": self.product.id,
                            "product_uom_qty": qty,
                            "product_uom": self.product.uom_id.id,
                            "location_id": self.supplier_location.id,
                            "location_dest_id": self.wh1.lot_stock_id.id,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()
        if validate:
            picking.move_ids.quantity = qty
            picking.move_ids.picked = True
            picking.button_validate()
        return picking

    def _assert_qty_to_order(self, qty_wh1, qty_wh2):
        self.assertEqual(self.orderpoint_wh1.qty_to_order_computed, qty_wh1)
        self.assertEqual(self.orderpoint_wh2.qty_to_order_computed, qty_wh2)

    def test_done_move_line_quantity_correction(self):
        receipt = self._receipt(6)
        self._assert_qty_to_order(4.0, 10.0)
        receipt.move_ids.move_line_ids.quantity = 0
        self._assert_qty_to_order(10.0, 10.0)

    def test_done_move_line_location_correction(self):
        receipt = self._receipt(6)
        self._assert_qty_to_order(4.0, 10.0)
        receipt.move_ids.move_line_ids.location_dest_id = self.wh2.lot_stock_id
        self._assert_qty_to_order(10.0, 4.0)

    def test_move_line_added_to_done_move(self):
        receipt = self._receipt(6)
        self._assert_qty_to_order(4.0, 10.0)
        self.env["stock.move.line"].create(
            {
                "move_id": receipt.move_ids.id,
                "picking_id": receipt.id,
                "product_id": self.product.id,
                "product_uom_id": self.product.uom_id.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.wh1.lot_stock_id.id,
                "quantity": 4,
            }
        )
        self._assert_qty_to_order(0.0, 10.0)

    def test_pending_move_destination_change(self):
        receipt = self._receipt(6, validate=False)
        self._assert_qty_to_order(4.0, 10.0)
        receipt.move_ids.location_dest_id = self.wh2.lot_stock_id
        self._assert_qty_to_order(10.0, 4.0)
