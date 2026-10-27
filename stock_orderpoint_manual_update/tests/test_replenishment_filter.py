from odoo import Command
from odoo.tests.common import TransactionCase


class TestReplenishmentFilter(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.customer_location = cls.env.ref("stock.stock_location_customers")
        cls.vendor_a, cls.vendor_b = cls.env["res.partner"].create([{"name": "Vendor A"}, {"name": "Vendor B"}])
        cls.categ_1, cls.categ_2 = cls.env["product.category"].create([{"name": "Categ 1"}, {"name": "Categ 2"}])

        def product(name, categ, vendors):
            return cls.env["product.product"].create(
                {
                    "name": name,
                    "is_storable": True,
                    "categ_id": categ.id,
                    "seller_ids": [
                        Command.create({"partner_id": vendor.id, "sequence": seq, "price": 10.0})
                        for seq, vendor in enumerate(vendors, 1)
                    ],
                }
            )

        cls.product_1 = product("Product 1", cls.categ_1, cls.vendor_a)
        cls.product_2 = product("Product 2", cls.categ_2, cls.vendor_b)
        # Vendor A is only its second vendor
        cls.product_3 = product("Product 3", cls.categ_1, cls.vendor_b | cls.vendor_a)
        cls.products = cls.product_1 | cls.product_2 | cls.product_3
        # A pending delivery of 5 leaves each product with a forecast of -5
        for prod in cls.products:
            cls._move(prod, 5.0)._action_confirm()

    @classmethod
    def _move(cls, product, qty):
        return cls.env["stock.move"].create(
            {
                "product_id": product.id,
                "product_uom_qty": qty,
                "location_id": cls.stock_location.id,
                "location_dest_id": cls.customer_location.id,
            }
        )

    def _orderpoints(self, products):
        return (
            self.env["stock.warehouse.orderpoint"]
            .with_context(active_test=False)
            .search([("product_id", "in", products.ids), ("location_id", "=", self.stock_location.id)])
        )

    def _confirm(self, **vals):
        action = self.env["stock.warehouse.orderpoint.wizard"].create(vals).action_confirm()
        shown = self.env["stock.warehouse.orderpoint"].with_context(active_test=False).search(action["domain"])
        return action, shown & self._orderpoints(self.products)

    def test_wizard_filters_replenishment(self):
        """The wizard only creates, refreshes and shows the replenishment rules that match its filters."""
        with self.subTest("filter by product"):
            action, shown = self._confirm(product_ids=[Command.set(self.product_1.ids)])
            # Only the filtered product gets a manual rule, the others are not computed
            self.assertEqual(self._orderpoints(self.products).product_id, self.product_1)
            self.assertEqual(shown.product_id, self.product_1)
            self.assertEqual(shown.qty_forecast_stored, -5.0)
            self.assertEqual(shown.qty_forecast_stored, shown.qty_forecast)

        with self.subTest("filter by category"):
            action, shown = self._confirm(category_ids=[Command.set(self.categ_1.ids)])
            self.assertEqual(self._orderpoints(self.products).product_id, self.product_1 | self.product_3)
            self.assertEqual(shown.product_id, self.product_1 | self.product_3)

        with self.subTest("filter by any vendor of the product"):
            self._confirm()
            action, shown = self._confirm(supplier_ids=[Command.set(self.vendor_a.ids)])
            self.assertEqual(shown.product_id, self.product_1 | self.product_3)

        with self.subTest("filter by the vendor set on the rule"):
            orderpoint_1 = self._orderpoints(self.product_1)
            orderpoint_1.supplier_id = self.product_1.seller_ids
            action, shown = self._confirm(
                supplier_ids=[Command.set(self.vendor_a.ids)],
                filter_by_main_supplier=True,
            )
            self.assertEqual(shown, orderpoint_1)

        with self.subTest("rotation is refreshed only when asked"):
            # The stored rotation is computed when first read, before the delivery
            self.assertEqual(orderpoint_1.rotation, 0.0)
            delivery = self._move(self.product_1, 8.0)
            delivery._action_confirm()
            delivery.quantity = 8.0
            delivery.picked = True
            delivery._action_done()
            self._confirm(product_ids=[Command.set(self.product_1.ids)])
            self.assertEqual(orderpoint_1.rotation, 0.0)
            self._confirm(product_ids=[Command.set(self.product_1.ids)], compute_rotation=True)
            # Rotation is the quantity delivered in 120 days divided by 4
            self.assertEqual(orderpoint_1.rotation, 2.0)

    def test_order_keeps_the_filter(self):
        """Ordering from the filtered list creates the RFQ and goes back to the same filtered list."""
        # Rules for every product, so that the filter has something to leave out
        self._confirm()
        orderpoint_2, orderpoint_3 = self._orderpoints(self.product_2), self._orderpoints(self.product_3)

        def order(orderpoint, **filters):
            # The wizard puts its filters in the context of the list
            result = orderpoint.with_context(**filters).action_replenish()
            self.assertEqual(result["tag"], "display_notification")
            next_action = result["params"]["next"]
            self.assertEqual(next_action["res_model"], "stock.warehouse.orderpoint")
            shown = self.env["stock.warehouse.orderpoint"].with_context(active_test=False).search(next_action["domain"])
            return shown & self._orderpoints(self.products)

        with self.subTest("filter by any vendor of the product"):
            shown = order(self._orderpoints(self.product_1), filter_suppliers=self.vendor_a.ids)
            purchase_line = self.env["purchase.order.line"].search([("product_id", "=", self.product_1.id)])
            self.assertEqual(purchase_line.order_id.partner_id, self.vendor_a)
            self.assertEqual(purchase_line.product_qty, 5.0)
            # Core deletes the ordered manual rule, so the list shows the other one of vendor A
            self.assertEqual(shown, orderpoint_3)

        with self.subTest("filter by product"):
            shown = order(orderpoint_3, filter_products=(self.product_2 | self.product_3).ids)
            self.assertEqual(shown, orderpoint_2)
