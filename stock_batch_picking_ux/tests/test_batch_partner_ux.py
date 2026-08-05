##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBatchPartnerUx(TransactionCase):
    """Cubre la interacción entre el compute de partner_id y el onchange que
    ajusta los traslados. Antes se peleaban y dejaban el campo Cliente inservible
    en un lote nuevo (ticket 124398)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_a = cls.env["res.partner"].create({"name": "Cliente A (124398)"})
        cls.partner_b = cls.env["res.partner"].create({"name": "Cliente B (124398)"})
        cls.product = cls.env["product.product"].create({"name": "Producto 124398", "is_storable": True})
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.picking_type_out = cls.warehouse.out_type_id
        cls.customer_loc = cls.env.ref("stock.stock_location_customers")

    def _new_delivery(self, partner):
        """Crea y confirma una entrega para que quede en un estado elegible
        (confirmed/assigned) para el batch."""
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_out.id,
                "partner_id": partner.id,
                "location_id": self.picking_type_out.default_location_src_id.id,
                "location_dest_id": self.customer_loc.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1,
                            "location_id": self.picking_type_out.default_location_src_id.id,
                            "location_dest_id": self.customer_loc.id,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()
        return picking

    def _new_batch(self):
        return self.env["stock.picking.batch"].create({"picking_type_id": self.picking_type_out.id})

    def test_partner_manual_persiste_en_lote_vacio(self):
        """Caso 1: en un lote sin traslados, fijar el Cliente a mano NO debe
        borrarse solo (era el bug: el compute lo volvía a False)."""
        with Form(self.env["stock.picking.batch"]) as form:
            form.picking_type_id = self.picking_type_out
            form.partner_id = self.partner_a
        batch = form.save()
        self.assertEqual(
            batch.partner_id,
            self.partner_a,
            "El cliente cargado a mano en un lote vacío no debe autoborrarse",
        )

    def test_partner_derivado_de_los_traslados(self):
        """Caso 2: al cargar traslados de un único cliente, el compute deriva
        ese cliente."""
        batch = self._new_batch()
        picking = self._new_delivery(self.partner_a)
        batch.picking_ids = [(6, 0, picking.ids)]
        self.assertEqual(batch.partner_id, self.partner_a)

    def test_cambio_de_cliente_filtra_en_vez_de_vaciar(self):
        """Caso 3: con traslados de dos clientes, fijar un cliente deja solo los
        que coinciden (antes vaciaba todo y el compute blanqueaba el cliente)."""
        picking_a = self._new_delivery(self.partner_a)
        picking_b = self._new_delivery(self.partner_b)
        batch = self._new_batch()
        # carga por backend: sin onchange, el compute ve 2 clientes -> vacío
        batch.picking_ids = [(6, 0, (picking_a + picking_b).ids)]
        self.assertFalse(batch.partner_id)

        with Form(batch) as form:
            form.partner_id = self.partner_a
        batch = form.save()

        self.assertEqual(
            batch.picking_ids,
            picking_a,
            "Solo deben quedar los traslados del cliente elegido",
        )
        self.assertEqual(
            batch.partner_id,
            self.partner_a,
            "El cliente elegido debe persistir (no debe autoborrarse)",
        )

    def test_multi_cliente_deja_partner_vacio(self):
        """Caso 4: un lote con traslados de varios clientes deja partner_id
        vacío (ambiguo)."""
        picking_a = self._new_delivery(self.partner_a)
        picking_b = self._new_delivery(self.partner_b)
        batch = self._new_batch()
        batch.picking_ids = [(6, 0, (picking_a + picking_b).ids)]
        self.assertFalse(batch.partner_id)

    def test_impresion_consolidada_vs_individual(self):
        """Caso 5: no rompimos la bifurcación del impreso — con cliente único va
        el remito consolidado del lote; sin cliente, los remitos individuales."""
        consolidated = self.env.ref("stock_batch_picking_ux.action_report_batch_deliveryslip")
        individual = self.env.ref("stock.action_report_delivery")

        # discard_logo_check evita que report_action devuelva el wizard de
        # configuración de layout (admin + compañía sin external_report_layout_id).
        picking_a = self._new_delivery(self.partner_a)
        batch_con = self._new_batch().with_context(discard_logo_check=True)
        batch_con.picking_ids = [(6, 0, picking_a.ids)]
        self.assertEqual(batch_con.partner_id, self.partner_a)
        action_con = batch_con.action_print_delivery_slip()
        self.assertEqual(action_con.get("report_name"), consolidated.report_name)

        picking_b = self._new_delivery(self.partner_b)
        batch_sin = self._new_batch().with_context(discard_logo_check=True)
        batch_sin.picking_ids = [(6, 0, (picking_a + picking_b).ids)]
        self.assertFalse(batch_sin.partner_id)
        action_sin = batch_sin.action_print_delivery_slip()
        self.assertEqual(action_sin.get("report_name"), individual.report_name)
