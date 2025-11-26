from .common import TestStockCurrencyValuationCommon


class TestInventoryAdjustmentInCurrency(TestStockCurrencyValuationCommon):
    """Tests de Op 6 y Op 7 (TESTING.md): ajustes de inventario sin picking.

    Aislados respecto al walkthrough combinado, con un estado inicial
    explícito: 10 unid @ 1000 ARS / 1.00 USD avg.
    """

    def _seed_avg_state(self):
        """Estado base: recepción 10 unid @ 1000 ARS rate Día 1.
        Deja el producto con qty=10, avg_in_currency=1.00, std_price=1000.
        """
        self._purchase_receipt(qty=10, price_unit=1000, inverse_rate=self.INVERSE_D1, date_str=self.DAY_1)
        product = self._product()
        self.assertEqual(product.qty_available, 10)
        self.assertAlmostEqual(product.standard_price_in_currency, 1.00, places=2)

    def test_positive_adjustment_preserves_avg(self):
        """Op 6: ajuste +3 sin picking se valúa a +qty × AVCO USD y deja el avg igual.

        Cubierto por la rama "sin picking" de `_set_value` — ver TESTING.md sección Op 6.
        """
        self._seed_avg_state()
        _quant, move = self._inventory_adjustment(new_qty=13, date_str=self.DAY_1)

        # move.value = 3 × 1000 = 3000 ARS, value_in_currency = 3 × 1.00 = 3.00 USD
        self.assertAlmostEqual(move.value, 3000, places=2)
        self.assertAlmostEqual(move.value_in_currency, 3.00, places=2)

        product = self._product()
        self.assertEqual(product.qty_available, 13)
        # avg en USD preservado (entró stock al AVCO actual)
        self.assertAlmostEqual(product.standard_price_in_currency, 1.00, places=2)
        self.assertAlmostEqual(product.total_value_in_currency, 13.00, places=2)

    def test_negative_adjustment_preserves_avg(self):
        """Op 7: ajuste -2 sin picking se valúa a qty × AVCO USD y deja el avg igual.

        Cubierto por la rama "sin picking" de `_set_value` — ver TESTING.md Op 7.
        """
        self._seed_avg_state()
        _quant, move = self._inventory_adjustment(new_qty=8, date_str=self.DAY_1)

        # Odoo 19: move.value es magnitud positiva (la dirección la da is_out).
        self.assertAlmostEqual(move.value, 2000, places=2)
        self.assertAlmostEqual(move.value_in_currency, 2.00, places=2)

        product = self._product()
        self.assertEqual(product.qty_available, 8)
        self.assertAlmostEqual(product.standard_price_in_currency, 1.00, places=2)
        self.assertAlmostEqual(product.total_value_in_currency, 8.00, places=2)

    def test_value_manual_in_currency_creates_product_value(self):
        """El usuario setea `move.value_manual_in_currency` sobre un ajuste sin picking;
        el inverse debe crear un `product.value` linkeado al move.

        No aserta el AVCO resultante (el replay actual no consume el product.value con
        `move_id` seteado — eso es discusión separada).
        """
        self._seed_avg_state()
        _quant, move = self._inventory_adjustment(new_qty=13, date_str=self.DAY_1)

        existing_values = self.env["product.value"].search([("move_id", "=", move.id)])
        existing_count = len(existing_values)

        # El ajuste ya quedó valuado en 3.00 (qty × AVCO); usamos un valor manual distinto
        # para forzar que el inverse cree el product.value.
        move.value_manual_in_currency = 5.00

        all_values = self.env["product.value"].search([("move_id", "=", move.id)])
        self.assertEqual(
            len(all_values),
            existing_count + 1,
            "Setear `value_manual_in_currency` debería crear un product.value linkeado al move.",
        )
        created = (all_values - existing_values)[:1]
        self.assertAlmostEqual(created.value_in_currency, 5.00, places=2)
        self.assertEqual(created.move_id, move)

    def test_value_manual_in_currency_zero_is_preserved(self):
        """Corregir `value_manual_in_currency` a 0 explícito no debe pisarse con el
        `standard_price_in_currency` vigente — `product.value.create()` sólo debe
        autocompletar cuando la clave está ausente, no cuando el valor es falsy.
        """
        self._seed_avg_state()
        _quant, move = self._inventory_adjustment(new_qty=13, date_str=self.DAY_1)

        # El ajuste quedó valuado en 3.00 (qty × AVCO), no en 0: forzamos el inverse
        # con una corrección manual explícita a cero.
        move.value_manual_in_currency = 0.0

        created = self.env["product.value"].search([("move_id", "=", move.id)], order="id desc", limit=1)
        self.assertEqual(created.move_id, move)
        self.assertAlmostEqual(
            created.value_in_currency,
            0.0,
            places=2,
            msg="El 0 explícito no debería pisarse con standard_price_in_currency.",
        )
