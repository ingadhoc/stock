##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests.common import TransactionCase


class TestForceTransferLeavesWave(TransactionCase):
    """force_transfer validates a picking directly; it must drop it from a wave whose
    other pickings are still open, or the wave keeps a done picking its sanity check rejects."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.src = cls.env.ref("stock.stock_location_stock")
        cls.dest = cls.env.ref("stock.stock_location_customers")
        cls.picking_type = cls.env.ref("stock.picking_type_out")
        cls.picking_type.write(
            {
                "auto_batch": True,
                "batch_group_by_partner": False,
                "batch_group_by_destination": False,
                "batch_group_by_src_loc": False,
                "batch_group_by_dest_loc": False,
                "wave_group_by_product": True,
                "wave_group_by_category": False,
                "wave_group_by_location": False,
            }
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Producto force_transfer test", "type": "consu", "is_storable": True}
        )
        cls.env["stock.quant"]._update_available_quantity(cls.product, cls.src, 10)

    def _new_assigned_picking(self):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type.id,
                "location_id": self.src.id,
                "location_dest_id": self.dest.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "name": self.product.name,
                            "product_id": self.product.id,
                            "product_uom_qty": 1.0,
                            "product_uom": self.product.uom_id.id,
                            "location_id": self.src.id,
                            "location_dest_id": self.dest.id,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()
        picking.action_assign()
        return picking

    def test_force_transfer_detaches_done_picking_from_open_wave(self):
        first = self._new_assigned_picking()
        wave = first.batch_id
        self.assertTrue(wave.is_wave)
        # A second picking of the same product auto-waves into the same wave.
        second = self._new_assigned_picking()
        self.assertEqual(second.batch_id, wave)

        first.force_transfer()

        self.assertEqual(first.state, "done")
        # The done picking left the wave; the open sibling keeps it.
        self.assertFalse(first.batch_id)
        self.assertEqual(second.batch_id, wave)
        # The wave is not left corrupt: every picking it still holds passes its sanity check.
        self.assertTrue(wave.picking_ids <= wave.allowed_picking_ids)
