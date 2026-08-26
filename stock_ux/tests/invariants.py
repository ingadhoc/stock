##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""Batería de invariantes de stock_ux.

Propiedades que tienen que valer después de *cualquier* operación de stock,
no lo que un escenario puntual fue a buscar. Se llaman después de cada
operación del test, y corren en todas las suites que hereden este mixin.

stock_ux es la raíz de la cadena Adhoc de stock (depende solo de core), así
que la batería vive acá: los 19 módulos propios que lo declaran en `depends`
la heredan sin copiarla.

Reglas de la batería (no negociables):

1. No tiene interruptores para saltear invariantes. Si un escenario
   legítimamente viola una, la excepción se declara en el test, a la vista.
2. Cada invariante tiene test propio en los dos sentidos: que no moleste a
   una operación sana, y que detecte la operación defectuosa.
"""

from odoo.tools import float_compare, float_is_zero


class StockUxInvariants:
    """Mixin de invariantes. Se hereda junto a TransactionCase."""

    def _uom_precision(self):
        return self.env["decimal.precision"].precision_get("Product Unit of Measure")

    def assert_sin_moves_extra(self, picking, esperado_por_producto):
        """El picking no gana movimientos que nadie pidió.

        Es la propiedad que fallaron los tickets de "contraentrega fantasma"
        (123822, 124773, 124957, 125936, 126226): al cancelar el remanente, el
        move negativo no netea y en vez de cancelar el pendiente queda un
        movimiento nuevo, en sentido contrario, que nadie pidió.

        :param esperado_por_producto: dict {product: cantidad demandada viva}
        """
        precision = self._uom_precision()
        vivos = picking.move_ids.filtered(lambda m: m.state != "cancel")
        # Ningún move vivo puede quedar en cantidad negativa: un negativo que
        # sobrevive es, exactamente, el movimiento que nadie pidió.
        negativos = vivos.filtered(lambda m: float_compare(m.product_uom_qty, 0.0, precision_digits=precision) < 0)
        self.assertFalse(
            negativos,
            "Quedaron moves en cantidad negativa (el neteo no ocurrió): %s"
            % negativos.mapped(lambda m: "%s: %s" % (m.product_id.display_name, m.product_uom_qty)),
        )
        # La demanda viva por producto es exactamente la esperada, ni más ni menos.
        real = {}
        for move in vivos:
            real[move.product_id] = real.get(move.product_id, 0.0) + move.product_uom_qty
        self.assertEqual(
            set(real.keys()),
            set(esperado_por_producto.keys()),
            "Los productos con demanda viva no son los esperados",
        )
        for product, cantidad in esperado_por_producto.items():
            self.assertEqual(
                float_compare(real[product], cantidad, precision_digits=precision),
                0,
                "La demanda viva de %s es %s y se esperaba %s" % (product.display_name, real[product], cantidad),
            )

    def assert_cantidad_no_supera_demanda(self, picking):
        """Con el tipo de operación bloqueando adicionales, ninguna cantidad
        transferida supera la demanda inicial."""
        if not picking.picking_type_id.block_additional_quantity:
            return
        precision = self._uom_precision()
        for move in picking.move_ids.filtered(lambda m: m.state != "cancel"):
            # Los ajustes de inventario están fuera del alcance del bloqueo (ver _check_quantity).
            if move.location_dest_usage == "inventory":
                continue
            self.assertLessEqual(
                float_compare(move.quantity, move.product_uom_qty, precision_digits=precision),
                0,
                "%s transfiere %s con demanda inicial %s"
                % (move.product_id.display_name, move.quantity, move.product_uom_qty),
            )

    def assert_sin_disponible_negativo(self, picking):
        """Ninguna ubicación interna del origen queda con disponible negativo
        para los productos del picking."""
        productos = picking.move_ids.product_id.filtered("is_storable")
        if not productos:
            return
        precision = self._uom_precision()
        ubicaciones = self.env["stock.location"].search(
            [
                ("id", "child_of", picking.location_id.id),
                ("usage", "=", "internal"),
                ("company_id", "in", [picking.company_id.id, False]),
            ]
        )
        if not ubicaciones:
            return
        quants = self.env["stock.quant"].search(
            [("product_id", "in", productos.ids), ("location_id", "in", ubicaciones.ids)]
        )
        negativos = quants.filtered(lambda q: float_compare(q.available_quantity, 0.0, precision_digits=precision) < 0)
        self.assertFalse(
            negativos,
            "Quedó disponible negativo en: %s"
            % negativos.mapped(
                lambda q: "%s @ %s: %s" % (q.product_id.display_name, q.location_id.name, q.available_quantity)
            ),
        )

    def assert_lineas_con_descripcion(self, picking):
        """Toda línea de operación del picking tiene descripción.

        stock_ux la completa en el create de stock.move.line con el idioma del
        contacto del picking; una línea sin descripción sale en blanco en el
        remito.
        """
        sin_descripcion = picking.move_line_ids.filtered(lambda l: not l.description_picking)
        self.assertFalse(
            sin_descripcion,
            "Líneas de operación sin descripción: %s" % sin_descripcion.mapped("product_id.display_name"),
        )

    def assert_estados_consistentes(self, picking):
        """Un picking validado deja todos sus moves en hecho o cancelado, y
        ningún move hecho en cantidad cero."""
        if picking.state != "done":
            return
        precision = self._uom_precision()
        colgados = picking.move_ids.filtered(lambda m: m.state not in ("done", "cancel"))
        self.assertFalse(
            colgados,
            "El picking está validado y quedaron moves en otro estado: %s"
            % colgados.mapped(lambda m: "%s: %s" % (m.product_id.display_name, m.state)),
        )
        en_cero = picking.move_ids.filtered(
            lambda m: m.state == "done" and float_is_zero(m.quantity, precision_digits=precision)
        )
        self.assertFalse(
            en_cero,
            "Moves hechos en cantidad cero: %s" % en_cero.mapped("product_id.display_name"),
        )

    def assert_sin_pickings_contraflujo(self, pickings, codigos_esperados):
        """El documento no genera pickings en sentido contrario al suyo.

        Las invariantes de arriba miran un picking por vez; esta mira el
        *conjunto* que un documento generó, que es donde vive la contraentrega:
        el picking pendiente no se cancela y aparece uno nuevo, de tipo
        contrario, que nadie pidió (121400, 122299, 123822, 124773, 125936,
        126226).

        Un picking fuera del flujo esperado solo es legítimo cuando es una
        devolución, y Odoo la marca poniendo ``origin_returned_move_id`` en
        todos sus moves.

        ``codigos_esperados`` es el parámetro que declara cada módulo
        consumidor: la forma de la invariante se comparte, el conjunto no.
        Una venta declara ``("outgoing", "internal")``; una compra,
        ``("incoming", "internal")``.
        """
        contraflujo = self.env["stock.picking"].browse()
        for picking in pickings.filtered(lambda p: p.state != "cancel"):
            if picking.picking_type_id.code in codigos_esperados:
                continue
            if any(not move.origin_returned_move_id for move in picking.move_ids):
                contraflujo |= picking
        self.assertFalse(
            contraflujo,
            "Pickings fuera del flujo esperado %s que no son devoluciones: %s"
            % (
                tuple(codigos_esperados),
                contraflujo.mapped(lambda p: "%s (%s)" % (p.name, p.picking_type_id.code)),
            ),
        )

    def assert_bateria(self, picking, esperado_por_producto=None):
        """Corre la batería entera. Es lo que se llama después de cada operación."""
        if esperado_por_producto is not None:
            self.assert_sin_moves_extra(picking, esperado_por_producto)
        self.assert_cantidad_no_supera_demanda(picking)
        self.assert_sin_disponible_negativo(picking)
        self.assert_lineas_con_descripcion(picking)
        self.assert_estados_consistentes(picking)

    def assert_bateria_documento(self, pickings, codigos_esperados):
        """Corre la batería sobre todos los pickings que generó un documento.

        Es el punto de entrada de los módulos cuyo documento genera más de un
        picking (una venta, una compra): verifica primero el conjunto y después
        cada picking por separado.
        """
        self.assert_sin_pickings_contraflujo(pickings, codigos_esperados)
        for picking in pickings:
            self.assert_bateria(picking)
