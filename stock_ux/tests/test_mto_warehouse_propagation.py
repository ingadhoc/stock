from odoo.addons.stock.tests.common import TestStockCommon
from odoo.tests import tagged


@tagged("stock_ux_mto")
class TestMtoWarehousePropagation(TestStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse_2 = cls.env["stock.warehouse"].create(
            {
                "name": "Secondary Warehouse",
                "code": "SWH",
                "company_id": cls.env.company.id,
                "partner_id": cls.env.company.partner_id.id,
                "reception_steps": "one_step",
                "delivery_steps": "ship_only",
            }
        )
        cls.customer_location_rec = cls.env["stock.location"].browse(cls.customer_location)

    def test_prepare_procurement_values_uses_physical_warehouse_for_mto(self):
        move = self._create_move(
            self.productA,
            self.warehouse_2.lot_stock_id,
            self.customer_location_rec,
            name="MTO stale warehouse",
            picking_type_id=self.warehouse_1.out_type_id.id,
            procure_method="make_to_order",
            warehouse_id=self.warehouse_1.id,
        )

        values = move._prepare_procurement_values()

        self.assertEqual(
            values["warehouse_id"],
            self.warehouse_2,
            "MTO procurements must use the physical warehouse of the source location.",
        )

    def test_prepare_procurement_values_keeps_non_mto_warehouse(self):
        move = self._create_move(
            self.productA,
            self.warehouse_2.lot_stock_id,
            self.customer_location_rec,
            name="MTS stale warehouse",
            picking_type_id=self.warehouse_1.out_type_id.id,
            procure_method="make_to_stock",
            warehouse_id=self.warehouse_1.id,
        )

        values = move._prepare_procurement_values()

        self.assertEqual(
            values["warehouse_id"],
            self.warehouse_1,
            "Non-MTO procurements should keep their propagated warehouse untouched.",
        )