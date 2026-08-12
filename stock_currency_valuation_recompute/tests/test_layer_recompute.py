from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestLayerRecompute(TransactionCase):
    def test_recompute_detects_out_valued_with_stale_cost(self):
        """Una salida valuada con el costo en moneda desactualizado tiene que salir marcada."""
        company = self.env.company
        categ = self.env["product.category"].create(
            {
                "name": "Categoria valuada en moneda",
                "property_cost_method": "average",
                "property_valuation": "manual_periodic",
                "valuation_currency_id": self.env.ref("base.USD").id,
            }
        )
        product = (
            self.env["product.product"]
            .create({"name": "Producto valuado en moneda", "is_storable": True, "categ_id": categ.id})
            .with_company(company)
        )
        product.standard_price = 1000.0
        product.standard_price_in_currency = 10.0

        warehouse = self.env["stock.warehouse"].search([("company_id", "=", company.id)], limit=1)
        quant = self.env["stock.quant"].with_context(inventory_mode=True)
        # ingreso 10 unidades
        quant.create(
            {
                "product_id": product.id,
                "location_id": warehouse.lot_stock_id.id,
                "inventory_quantity": 10.0,
            }
        ).action_apply_inventory()

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
        quant.search([("product_id", "=", product.id), ("location_id", "=", warehouse.lot_stock_id.id)]).write(
            {"inventory_quantity": 8.0}
        )
        quant.search(
            [("product_id", "=", product.id), ("location_id", "=", warehouse.lot_stock_id.id)]
        ).action_apply_inventory()

        recompute = self.env["stock.valuation.layer.recompute"].create(
            {"company_id": company.id, "product_id": product.id}
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
