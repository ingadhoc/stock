##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests.common import TransactionCase


class TestAutoWaveSkipCorruptWave(TransactionCase):
    """Auto-waving skips a wave already holding incompatible pickings instead of crashing."""

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
            {"name": "Producto auto-wave test", "type": "consu", "is_storable": True}
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

    def test_auto_wave_skips_corrupt_wave(self):
        victim = self._new_assigned_picking()
        wave = victim.batch_id
        self.assertTrue(wave.is_wave)
        self.assertEqual(wave.state, "in_progress")

        # Force an inconsistent state the ORM would not allow: the wave keeps a
        # picking that no longer satisfies its sanity check.
        self.env.cr.execute("UPDATE stock_picking SET state = 'draft' WHERE id = %s", (victim.id,))
        victim.invalidate_recordset(["state"])
        self.assertFalse(wave.picking_ids <= wave.allowed_picking_ids)

        # Reserving a new picking of the same product triggers auto-wave.
        new_picking = self._new_assigned_picking()

        self.assertEqual(new_picking.state, "assigned")
        self.assertTrue(new_picking.batch_id.is_wave)
        self.assertNotEqual(new_picking.batch_id, wave)
