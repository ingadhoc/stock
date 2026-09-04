from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestScrapLocationFollowsMove(TransactionCase):
    """La ubicación de origen del desecho sigue a la de su movimiento, que es donde se
    la puede corregir una vez hecho."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.location = cls.warehouse.lot_stock_id
        cls.other_location = cls.env["stock.location"].create(
            {
                "name": "Otro Stock",
                "usage": "internal",
                "location_id": cls.warehouse.view_location_id.id,
                "company_id": cls.env.company.id,
            }
        )
        cls.product = cls.env["product.product"].create({"name": "Producto a desechar", "is_storable": True})

    def test_location_follows_corrected_move_line(self):
        self.env["stock.quant"]._update_available_quantity(self.product, self.location, 5)
        scrap = self.env["stock.scrap"].create(
            {
                "product_id": self.product.id,
                "product_uom_id": self.product.uom_id.id,
                "scrap_qty": 1,
                "location_id": self.location.id,
            }
        )
        scrap.do_scrap()
        self.assertEqual(scrap.location_id, self.location)

        scrap.move_ids.move_line_ids.location_id = self.other_location
        self.assertEqual(scrap.location_id, self.other_location)
