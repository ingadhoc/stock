##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests.common import TransactionCase


class TestAutoWaveSkipCorruptWave(TransactionCase):
    """El armado automatico de olas no debe caerse por una ola ya corrupta.

    Reproduce el escenario del ticket 132370 / tarea 79477: una ola en progreso
    que quedo con un traslado en un estado que su _sanity_check ya no admite.
    Al reservar un traslado nuevo del mismo producto, el auto-wave la tomaba
    como candidata, intentaba sumarle la linea y hacia saltar un UserError que
    revertia toda la operacion (y, cuando el disparador es el programador de
    abastecimiento, la corrida entera: nunca avanza y se reintenta sin fin).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.src = cls.env.ref("stock.stock_location_stock")
        cls.dest = cls.env.ref("stock.stock_location_customers")
        cls.picking_type = cls.env.ref("stock.picking_type_out")
        # Armado automatico de olas agrupadas por producto (config del cliente).
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

    def test_auto_wave_skips_corrupt_wave(self):
        # La primera reserva arma (o toma) una ola con el picking victima.
        victim = self._new_assigned_picking()
        wave = victim.batch_id
        self.assertTrue(wave.is_wave, "El picking deberia haber entrado a una ola")
        self.assertEqual(wave.state, "in_progress")

        # Corrompemos la ola como pasa en produccion con el correr del tiempo:
        # el traslado queda en un estado que allowed_picking_ids ya no admite.
        # Lo forzamos por SQL porque la API nativa mantiene la ola consistente;
        # justamente ese dato inconsistente es lo que reproducimos.
        self.env.cr.execute("UPDATE stock_picking SET state = 'draft' WHERE id = %s", (victim.id,))
        victim.invalidate_recordset(["state"])
        self.assertFalse(
            wave.picking_ids <= wave.allowed_picking_ids,
            "La ola deberia haber quedado corrupta para el test",
        )

        # Reservar un traslado nuevo del mismo producto dispara el auto-wave.
        # Sin el fix, esto levantaba UserError al querer sumarlo a la ola corrupta.
        new_picking = self._new_assigned_picking()

        self.assertEqual(new_picking.state, "assigned")
        self.assertTrue(
            new_picking.batch_id.is_wave,
            "El traslado nuevo deberia haber entrado a una ola",
        )
        self.assertNotEqual(
            new_picking.batch_id,
            wave,
            "El traslado nuevo no debe entrar a la ola corrupta",
        )

    def test_auto_wave_still_merges_into_healthy_wave(self):
        """Guardia anti sobre-exclusion: una ola sana sigue recibiendo pickings.

        Si el fix descartara olas de mas, el armado automatico dejaria de
        agrupar y haria una ola por traslado. Dos traslados del mismo producto,
        con la ola sana, tienen que terminar en la MISMA ola.
        """
        first = self._new_assigned_picking()
        wave = first.batch_id
        self.assertTrue(wave.is_wave)
        self.assertTrue(
            wave.picking_ids <= wave.allowed_picking_ids,
            "La ola deberia estar sana",
        )

        second = self._new_assigned_picking()

        self.assertEqual(
            second.batch_id,
            wave,
            "El segundo traslado del mismo producto debe entrar a la ola sana existente",
        )
