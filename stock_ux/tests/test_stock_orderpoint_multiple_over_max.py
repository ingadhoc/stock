from odoo.tests.common import TransactionCase


class TestStockOrderpointMultipleOverMax(TransactionCase):
    def setUp(self):
        super().setUp()
        self.warehouse = self.env["stock.warehouse"].search([("company_id", "=", self.env.company.id)], limit=1)
        self.product = self.env["product.product"].create(
            {
                "name": "Reordering Rule Multiple Product",
                "is_storable": True,
            }
        )
        self.env["stock.quant"]._update_available_quantity(self.product, self.warehouse.lot_stock_id, 4)

    def _create_orderpoint(self, qty_multiple_over_max="company"):
        orderpoint = self.env["stock.warehouse.orderpoint"].create(
            {
                "name": f"Orderpoint {qty_multiple_over_max}",
                "product_id": self.product.id,
                "location_id": self.warehouse.lot_stock_id.id,
                "product_min_qty": 5,
                "product_max_qty": 10,
                "qty_multiple": 20,
                "qty_multiple_over_max": qty_multiple_over_max,
            }
        )
        orderpoint._compute_qty()
        orderpoint._compute_qty_to_order_computed()
        return orderpoint

    def test_company_setting_allows_rounding_over_max(self):
        self.env.company.stock_orderpoint_allow_multiple_over_max = True
        orderpoint = self._create_orderpoint()

        self.assertEqual(orderpoint.qty_to_order_computed, 20.0)

    def test_orderpoint_can_override_company_setting(self):
        self.env.company.stock_orderpoint_allow_multiple_over_max = True
        orderpoint = self._create_orderpoint(qty_multiple_over_max="restrict")

        self.assertEqual(orderpoint.qty_to_order_computed, 0.0)

    def test_orderpoint_can_force_legacy_behavior(self):
        self.env.company.stock_orderpoint_allow_multiple_over_max = False
        orderpoint = self._create_orderpoint(qty_multiple_over_max="allow")

        self.assertEqual(orderpoint.qty_to_order_computed, 20.0)
