from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger

MODEL_LOGGER = "odoo.addons.stock_currency_valuation_recompute.models.stock_valuation_layer_recompute"


@tagged("post_install", "-at_install")
class TestLayerRecompute(TransactionCase):
    def test_recompute_detects_out_valued_with_stale_cost(self):
        """Una salida valuada con el costo en moneda desactualizado tiene que salir marcada."""
        product, revaluation_layer = self._make_product_with_drift("Producto valuado en moneda")

        recompute = self.env["stock.valuation.layer.recompute"].create(
            {"company_id": self.env.company.id, "product_id": product.id}
        )
        recompute.action_compute_lines()

        self.assertEqual(recompute.state, "in_process", "Tiene que haber detectado diferencias")
        self.assertTrue(recompute.line_ids, "Tiene que armar una linea por layer")
        self.assertAlmostEqual(recompute.initial_amount_in_currency, 10.0, places=2)
        # el recalculo reparte los 50 USD de la revaluacion sobre las 10 unidades
        self.assertAlmostEqual(recompute.final_amount_in_currency, 15.0, places=2)
        self.assertTrue(
            recompute.line_ids.filtered("need_changes"),
            "La salida valuada con el costo viejo tiene que quedar marcada para ajustar",
        )
        # el ajuste manual y todo lo anterior se respeta: solo se toca lo posterior
        adjustment = recompute.line_ids.filtered(lambda x: x.layer_id == revaluation_layer)
        self.assertTrue(adjustment, "El ajuste manual tiene que aparecer como linea")
        self.assertFalse(adjustment.need_changes, "El ajuste manual no se toca")
        self.assertEqual(
            recompute.last_manual_svl_id,
            revaluation_layer,
            "Tiene que detectar el ajuste manual sin importar quien lo cargo",
        )
        for line in recompute.line_ids.filtered("need_changes"):
            self.assertGreater(
                line.layer_id.id, revaluation_layer.id, "Solo se marcan layers posteriores al ajuste manual"
            )

        # los layers que no se van a escribir avanzan el promedio con su valor registrado,
        # para que el costo final cierre contra lo que efectivamente queda en la base
        for line in recompute.line_ids.filtered(lambda x: not x.need_changes):
            self.assertEqual(
                line.new_value_in_currency,
                line.layer_value_in_currency,
                "Un layer que no se escribe no puede aportar al promedio un valor distinto al registrado",
            )
            self.assertEqual(line.new_value, line.layer_value)

    def test_compute_lines_multi_processes_every_selected_record(self):
        """El boton de la lista recalcula cada registro de la seleccion, no solo el primero."""
        Recompute = self.env["stock.valuation.layer.recompute"]
        recomputes = Recompute.create(
            [
                {"company_id": self.env.company.id, "product_id": self._make_product_with_layer("Producto A").id},
                {"company_id": self.env.company.id, "product_id": self._make_product_with_layer("Producto B").id},
            ]
        )

        recomputes.action_compute_lines_multi()

        for recompute in recomputes:
            self.assertTrue(recompute.line_ids, "Cada registro seleccionado tiene que quedar recalculado")
            self.assertNotEqual(recompute.state, "draft")

    @mute_logger(MODEL_LOGGER)
    def test_compute_lines_multi_isolates_the_record_that_fails(self):
        """Un producto no soportado no puede tirar abajo el recalculo de toda la seleccion."""
        Recompute = self.env["stock.valuation.layer.recompute"]
        failing = Recompute.create(
            {"company_id": self.env.company.id, "product_id": self._make_product("Por lote", by_lot=True).id}
        )
        healthy = Recompute.create(
            {"company_id": self.env.company.id, "product_id": self._make_product_with_layer("Producto sano").id}
        )

        (failing | healthy).action_compute_lines_multi()

        self.assertEqual(failing.state, "error")
        self.assertTrue(failing.revaluation_error, "Tiene que quedar el motivo a la vista")
        self.assertTrue(healthy.line_ids, "El que falla no puede arrastrar al resto de la seleccion")

    def test_queue_revaluation_has_no_limit(self):
        """Encolar es una escritura de estado: no hay tope de cuantos se pueden mandar."""
        recomputes = self.env["stock.valuation.layer.recompute"].create(
            [{"company_id": self.env.company.id} for _unused in range(35)]
        )
        recomputes.state = "in_process"

        recomputes.action_queue_revaluation()

        self.assertEqual(set(recomputes.mapped("state")), {"revaluating"})

    def test_cron_drains_the_queue(self):
        """El cron aplica lo encolado y lo deja en done."""
        recompute = self._make_computed_recompute("Producto A")
        recompute.action_queue_revaluation()

        self.env["stock.valuation.layer.recompute"]._cron_revaluate_queued()

        self.assertEqual(recompute.state, "done")

    def test_cron_respects_a_record_taken_out_of_the_queue(self):
        """Si lo cancelan despues de encolarlo, el cron no lo aplica igual."""
        Recompute = self.env["stock.valuation.layer.recompute"]
        stays = self._make_computed_recompute("Producto A")
        cancelled = self._make_computed_recompute("Producto B")
        (stays | cancelled).action_queue_revaluation()
        cancelled.action_cancel()

        Recompute._cron_revaluate_queued()

        self.assertEqual(cancelled.state, "cancel", "Cancelar tiene que sacarlo de la cola de verdad")
        self.assertEqual(stays.state, "done")

    def test_a_record_without_lines_cannot_be_revaluated(self):
        """Aplicar sin lineas calculadas pondria el costo del producto en cero."""
        recompute = self.env["stock.valuation.layer.recompute"].create(
            {"company_id": self.env.company.id, "product_id": self._make_product("Producto A").id}
        )
        recompute.state = "in_process"

        with self.assertRaises(UserError):
            recompute.action_manual_slv_revaluation()

    def test_a_failed_compute_cannot_be_queued_for_revaluation(self):
        """Un registro que quedo en error por el recalculo no se encola: hay que recalcular."""
        recompute = self.env["stock.valuation.layer.recompute"].create(
            {"company_id": self.env.company.id, "product_id": self._make_product("Producto A").id}
        )
        recompute.write({"state": "error", "revaluation_error": "fallo el recalculo"})

        with self.assertRaises(UserError):
            recompute.action_queue_revaluation()

    def test_a_retry_that_works_clears_the_previous_error(self):
        """El motivo de una falla vieja no puede sobrevivir a un recalculo exitoso."""
        recompute = self.env["stock.valuation.layer.recompute"].create(
            {"company_id": self.env.company.id, "product_id": self._make_product_with_layer("Producto A").id}
        )
        recompute.write({"state": "error", "revaluation_error": "fallo la vez pasada"})

        recompute.action_compute_lines()

        self.assertFalse(recompute.revaluation_error, "Un registro sano no puede mostrar un motivo de falla")

    def test_a_manual_revaluation_can_be_corrected_in_two_passes(self):
        """Corregir a mano una revaluacion, y que el recompute siguiente la respete.

        Es el recorrido que le queda al operador para arreglar una revaluacion cuyo valor
        en la moneda secundaria se cargo mal: el recalculo no la toca por diseno, asi que
        la correccion se tilda a mano y el segundo recompute reacomoda todo lo posterior.
        """
        Recompute = self.env["stock.valuation.layer.recompute"]
        product, adjustment = self._make_product_with_drift("Producto A")

        # pasada 1: tildo la linea del ajuste, la corrijo, y destildo las demas
        first = Recompute.create({"company_id": self.env.company.id, "product_id": product.id})
        first.action_compute_lines()
        adjustment_line = first.line_ids.filtered(lambda line: line.layer_id == adjustment)
        self.assertFalse(adjustment_line.need_changes, "El ajuste manual sale sin marcar")
        value_in_company_currency = adjustment.value
        adjustment_line.need_changes = True
        adjustment_line.new_value_in_currency = 30.0
        (first.line_ids - adjustment_line).need_changes = False

        first.action_manual_slv_revaluation()

        self.assertEqual(adjustment.value_in_currency, 30.0, "La correccion tiene que aplicarse")
        self.assertEqual(adjustment.value, value_in_company_currency, "El importe en pesos no cambia")

        # pasada 2: recompute nuevo, sin tocar nada a mano
        second = Recompute.create({"company_id": self.env.company.id, "product_id": product.id})
        second.action_compute_lines()
        second_line = second.line_ids.filtered(lambda line: line.layer_id == adjustment)
        self.assertEqual(second_line.new_value_in_currency, 30.0, "Tiene que respetar la correccion")
        self.assertFalse(second_line.need_changes, "Y no querer volver a escribirla")

        second.action_manual_slv_revaluation()

        layers = self.env["stock.valuation.layer"].search(
            [("product_id", "=", product.id), ("company_id", "=", self.env.company.id)]
        )
        self.assertAlmostEqual(
            product.standard_price_in_currency * sum(layers.mapped("quantity")),
            sum(layers.mapped("value_in_currency")),
            places=2,
            msg="Despues de la segunda pasada el costo tiene que cerrar contra la suma de capas",
        )

    def test_queue_revaluation_skips_records_already_applied(self):
        """Encolar en masa no vuelve a mandar un registro ya aplicado."""
        recompute = self.env["stock.valuation.layer.recompute"].create({"company_id": self.env.company.id})
        recompute.state = "done"

        with self.assertRaises(UserError):
            recompute.action_queue_revaluation()

    def _make_computed_recompute(self, name):
        """Recompute ya calculado y con diferencias, o sea aplicable."""
        product, _revaluation_layer = self._make_product_with_drift(name)
        recompute = self.env["stock.valuation.layer.recompute"].create(
            {"company_id": self.env.company.id, "product_id": product.id}
        )
        recompute.action_compute_lines()
        self.assertEqual(recompute.state, "in_process", "El fixture tiene que dar diferencias")
        return recompute

    def _make_product_with_drift(self, name):
        """Producto cuyo costo en moneda quedo desalineado de sus layers: el caso que el
        modulo repara. Devuelve el producto y el layer del ajuste manual."""
        company = self.env.company
        product = self._make_product_with_layer(name)
        warehouse = self.env["stock.warehouse"].search([("company_id", "=", company.id)], limit=1)
        quant = self.env["stock.quant"].with_context(inventory_mode=True)

        # revaluacion que en 18.0 no impactaba la ficha: el layer queda en 50 USD
        # pero el costo en moneda del producto sigue en 10
        revaluation_layer = self.env["stock.valuation.layer"].create(
            {
                "company_id": company.id,
                "product_id": product.id,
                "description": "Manual Stock Valuation: test.",
                "value": 5000.0,
                "value_in_currency": 50.0,
                "quantity": 0,
            }
        )

        # salida de 2 unidades, valuada con el costo en moneda desactualizado
        domain = [("product_id", "=", product.id), ("location_id", "=", warehouse.lot_stock_id.id)]
        quant.search(domain).write({"inventory_quantity": 8.0})
        quant.search(domain).action_apply_inventory()
        return product, revaluation_layer

    def _make_product(self, name, by_lot=False):
        """Producto valuado en moneda, opcionalmente valuado por lote (caso no soportado)."""
        categ = self.env["product.category"].create(
            {
                "name": name,
                "property_cost_method": "average",
                "property_valuation": "manual_periodic",
                "valuation_currency_id": self.env.ref("base.USD").id,
            }
        )
        vals = {"name": name, "is_storable": True, "categ_id": categ.id}
        if by_lot:
            vals.update({"tracking": "lot", "lot_valuated": True})
        return self.env["product.product"].create(vals).with_company(self.env.company)

    def _make_product_with_layer(self, name):
        """Producto valuado en moneda con una capa de valuacion, lo minimo para recalcular."""
        product = self._make_product(name)
        product.standard_price = 1000.0
        product.standard_price_in_currency = 10.0
        warehouse = self.env["stock.warehouse"].search([("company_id", "=", self.env.company.id)], limit=1)
        self.env["stock.quant"].with_context(inventory_mode=True).create(
            {
                "product_id": product.id,
                "location_id": warehouse.lot_stock_id.id,
                "inventory_quantity": 10.0,
            }
        ).action_apply_inventory()
        return product
