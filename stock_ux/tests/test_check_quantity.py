from odoo.addons.stock.tests.common import TestStockCommon
from odoo.exceptions import ValidationError
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestCheckQuantity(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env_su = cls.env(su=True)
        cls.product_serial = env_su["product.product"].create(
            {"name": "Serial product", "is_storable": True, "tracking": "serial"}
        )
        cls.lot = env_su["stock.lot"].create({"name": "SN-0001", "product_id": cls.product_serial.id})
        env_su["stock.quant"]._update_available_quantity(cls.product_serial, cls.stock_location, 1.0, lot_id=cls.lot)
        cls.user_stock_manager.sudo().write({"company_ids": [(4, cls.company.id)], "company_id": cls.company.id})

    def _receipt(self, product, qty, lot=False):
        env = self.env(user=self.user_stock_manager)
        picking = env["stock.picking"].create(
            {
                "picking_type_id": self.warehouse_1.in_type_id.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_uom_qty": qty,
                            "location_id": self.supplier_location.id,
                            "location_dest_id": self.stock_location.id,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()
        move_line_vals = {"quantity": qty}
        if lot:
            move_line_vals["lot_id"] = lot.id
        if picking.move_ids.move_line_ids:
            picking.move_ids.move_line_ids.write(move_line_vals)
        else:
            picking.move_ids.move_line_ids = [(0, 0, dict(move_line_vals, product_id=product.id))]
        picking.move_ids.picked = True
        return picking

    def test_duplicated_serial_is_blocked(self):
        picking = self._receipt(self.product_serial, 1.0, lot=self.lot)
        with self.assertRaises(ValidationError):
            picking.button_validate()

    def test_block_additional_quantity(self):
        self.warehouse_1.in_type_id.with_user(self.user_stock_manager).block_additional_quantity = True
        picking = self._receipt(self.productA, 2.0)
        with self.assertRaises(ValidationError):
            picking.move_ids.quantity = 3.0
