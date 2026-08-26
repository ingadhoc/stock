##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""La batería, probada en los dos sentidos.

Cada invariante se verifica dos veces: que no moleste a una operación sana, y
que detecte la operación defectuosa que existe para atajar. Sin la segunda no
sabemos si la invariante mira.
"""

from odoo.tests import Form

from .common import StockUxCommon


class TestInvariants(StockUxCommon):
    def setUp(self):
        super().setUp()
        self._poner_stock(self.product, 50.0)
        self.picking = self._crear_picking(lineas=[(self.product, 10.0)])
        self.picking.action_confirm()

    # --- I1: el picking no gana movimientos que nadie pidió --------------

    def test_sin_moves_extra_no_molesta_a_una_operacion_sana(self):
        # Un picking con su demanda intacta pasa la invariante
        self.assert_sin_moves_extra(self.picking, {self.product: 10.0})

    def test_sin_moves_extra_detecta_el_negativo_que_sobrevive(self):
        # Un move negativo que no neteó es la contraentrega fantasma
        self.picking.move_ids[0].copy({"product_uom_qty": -4.0})
        with self.assertRaises(AssertionError):
            self.assert_sin_moves_extra(self.picking, {self.product: 10.0})

    def test_sin_moves_extra_detecta_la_demanda_que_no_cierra(self):
        # Un move extra del mismo producto infla la demanda viva
        self.picking.move_ids[0].copy({"product_uom_qty": 3.0})
        with self.assertRaises(AssertionError):
            self.assert_sin_moves_extra(self.picking, {self.product: 10.0})

    # --- I2: ninguna cantidad supera la demanda inicial -------------------

    def test_cantidad_no_supera_demanda_no_molesta_a_una_operacion_sana(self):
        # Transferir exactamente lo demandado pasa la invariante
        self.picking.picking_type_id.block_additional_quantity = True
        self.picking.move_ids.quantity = 10.0
        self.assert_cantidad_no_supera_demanda(self.picking)

    def test_cantidad_no_supera_demanda_detecta_el_exceso(self):
        # La cantidad se carga con el bloqueo apagado y se enciende después:
        # así el estado defectuoso existe sin pasar por el constrain del módulo
        self.picking.move_ids.quantity = 12.0
        self.picking.picking_type_id.block_additional_quantity = True
        with self.assertRaises(AssertionError):
            self.assert_cantidad_no_supera_demanda(self.picking)

    # --- I3: ninguna ubicación interna queda con disponible negativo ------

    def test_sin_disponible_negativo_no_molesta_a_una_operacion_sana(self):
        self.assert_sin_disponible_negativo(self.picking)

    def test_sin_disponible_negativo_detecta_el_quant_en_rojo(self):
        # Dejamos la ubicación de origen en rojo para el producto del picking
        self._poner_stock(self.product, -60.0)
        with self.assertRaises(AssertionError):
            self.assert_sin_disponible_negativo(self.picking)

    # --- I4: toda línea de operación tiene descripción --------------------

    def test_lineas_con_descripcion_no_molesta_a_una_operacion_sana(self):
        self.picking.action_assign()
        self.assertTrue(self.picking.move_line_ids, "El escenario necesita líneas reservadas")
        self.assert_lineas_con_descripcion(self.picking)

    def test_lineas_con_descripcion_detecta_la_linea_en_blanco(self):
        self.picking.action_assign()
        self.picking.move_line_ids[0].description_picking = False
        with self.assertRaises(AssertionError):
            self.assert_lineas_con_descripcion(self.picking)

    # --- I5: el picking validado deja estados consistentes ----------------

    def test_estados_consistentes_no_molesta_a_una_operacion_sana(self):
        self.picking.action_assign()
        self.picking.move_ids.quantity = 10.0
        self.picking.button_validate()
        self.assertEqual(self.picking.state, "done")
        self.assert_estados_consistentes(self.picking)

    def test_estados_consistentes_detecta_el_move_hecho_en_cero(self):
        self.picking.action_assign()
        self.picking.move_ids.quantity = 10.0
        self.picking.button_validate()
        # Vaciamos la línea de un move ya hecho: queda un move done sin cantidad
        self.picking.move_line_ids.write({"quantity": 0.0})
        with self.assertRaises(AssertionError):
            self.assert_estados_consistentes(self.picking)

    def test_estados_consistentes_no_verifica_un_picking_sin_validar(self):
        # La invariante solo habla de pickings validados: sobre uno abierto no opina
        self.assertNotEqual(self.picking.state, "done")
        self.assert_estados_consistentes(self.picking)

    # --- I6: el documento no genera pickings en sentido contrario ---------

    VENTA = ("outgoing", "internal")

    def test_sin_pickings_contraflujo_no_molesta_a_una_devolucion_genuina(self):
        # Una devolución real es un picking de entrada legítimo: no es contraflujo
        self.picking.action_assign()
        self.picking.move_ids.quantity = 10.0
        self.picking.button_validate()
        wizard = Form(
            self.env["stock.return.picking"].with_context(
                active_id=self.picking.id, active_ids=self.picking.ids, active_model="stock.picking"
            )
        ).save()
        # El wizard nace en cantidad cero: sin esto no hay nada que devolver
        wizard.product_return_moves.quantity = 10.0
        devolucion = self.env["stock.picking"].browse(wizard.action_create_returns()["res_id"])
        self.assertEqual(devolucion.picking_type_id.code, "incoming", "El escenario necesita una devolución entrante")

        self.assert_sin_pickings_contraflujo(self.picking | devolucion, self.VENTA)

    def test_sin_pickings_contraflujo_detecta_la_contraentrega(self):
        # Una recepción que nadie devolvió: la forma exacta de la contraentrega
        contraentrega = self._crear_picking(picking_type=self.in_type, lineas=[(self.product, 4.0)])
        self.assertFalse(contraentrega.move_ids.origin_returned_move_id)

        with self.assertRaises(AssertionError):
            self.assert_sin_pickings_contraflujo(self.picking | contraentrega, self.VENTA)

    def test_bateria_documento_recorre_el_conjunto_y_cada_picking(self):
        # El runner de documento verifica el conjunto y después picking por picking
        self.assert_bateria_documento(self.picking, self.VENTA)
        contraentrega = self._crear_picking(picking_type=self.in_type, lineas=[(self.product, 4.0)])
        with self.assertRaises(AssertionError):
            self.assert_bateria_documento(self.picking | contraentrega, self.VENTA)

    # --- la batería completa ----------------------------------------------

    def test_bateria_completa_sobre_una_entrega_sana(self):
        # Una entrega normal, de punta a punta, no viola ninguna invariante
        self.assert_bateria(self.picking, {self.product: 10.0})
        self.picking.action_assign()
        self.assert_bateria(self.picking, {self.product: 10.0})
        self.picking.move_ids.quantity = 10.0
        self.picking.button_validate()
        self.assert_bateria(self.picking, {self.product: 10.0})
