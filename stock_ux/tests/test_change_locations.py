from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestChangeLocations(TransactionCase):
    """Change Locations gets the selected lines from the list it is called from: it read
    them from a context key the client no longer sends, so it confirmed and changed nothing."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids += cls.env.ref("stock.group_stock_manager")
        cls.stock = cls.env.ref("stock.stock_location_stock")
        cls.shelf = cls.env["stock.location"].create({"name": "Shelf", "location_id": cls.stock.id})
        cls.customers = cls.env.ref("stock.stock_location_customers")
        cls.products = cls.env["product.product"].create(
            [{"name": name, "is_storable": True} for name in ("Product One", "Product Two")]
        )
        for product in cls.products:
            cls.env["stock.quant"]._update_available_quantity(product, cls.stock, 5)
            cls.env["stock.quant"]._update_available_quantity(product, cls.shelf, 5)
        cls.picking = cls.env["stock.picking"].create(
            {
                "picking_type_id": cls.env.ref("stock.picking_type_out").id,
                "location_id": cls.stock.id,
                "location_dest_id": cls.customers.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": p.id,
                            "product_uom_qty": 2,
                            "location_id": cls.stock.id,
                            "location_dest_id": cls.customers.id,
                        },
                    )
                    for p in cls.products
                ],
            }
        )
        cls.picking.action_confirm()
        cls.picking.action_assign()

    def test_selected_lines_get_the_new_locations(self):
        lines = self.picking.move_line_ids
        self.assertEqual(len(lines), 2)
        wizard = (
            self.env["stock.operation.wizard"]
            .with_context(active_model="stock.move.line", active_ids=lines.ids)
            .create({"location_id": self.shelf.id, "location_dest_id": self.customers.id})
        )
        self.assertEqual(wizard.picking_id, self.picking)
        wizard.action_change_location()
        self.assertEqual(lines.location_id, self.shelf)
