from odoo.addons.stock.tests.common import TestStockCommon
from odoo.tests import tagged


@tagged("stock_ux_picking_location_dest")
class TestPickingLocationDest(TestStockCommon):
    def test_create_propagates_location_dest_to_moves(self):
        """Una linea guardada con el destino del tipo de operacion debe tomar el de la cabecera."""
        picking_type = self.warehouse_1.int_type_id
        assembly = self.StockLocationObj.create(
            {
                "name": "Assembly",
                "location_id": picking_type.default_location_dest_id.location_id.id,
                "usage": "transit",
            }
        )
        picking_type.default_location_dest_id = assembly
        picking = self.PickingObj.create(
            {
                "picking_type_id": picking_type.id,
                "location_id": picking_type.default_location_src_id.id,
                "location_dest_id": self.warehouse_1.lot_stock_id.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "name": self.productA.name,
                            "product_id": self.productA.id,
                            "product_uom_qty": 1,
                            "location_id": picking_type.default_location_src_id.id,
                            # el cliente web puede mandar el destino por defecto del tipo
                            "location_dest_id": assembly.id,
                        },
                    )
                ],
            }
        )
        self.assertEqual(picking.move_ids.location_dest_id, self.warehouse_1.lot_stock_id)
