from .common import TestStockCurrencyValuationCommon


class TestDeliveryAndReturn(TestStockCurrencyValuationCommon):
    """Tests de Op 4 (entrega) y Op 5 (devolución) — TESTING.md."""

    def _seed_two_receipts(self):
        """Estado base para Op 4/5: 20 unid, total_value_in_currency = 30.17, avg ≈ 1.51."""
        self._purchase_receipt(qty=10, price_unit=1000, inverse_rate=self.INVERSE_D1, date_str=self.DAY_1)
        # LC sobre la primera recepción (Op 2 con rate Día 2)
        self._landed_cost(
            picking=self.env["stock.picking"].search([("partner_id", "=", self.vendor.id)], order="id desc", limit=1),
            amount=200,
            inverse_rate=self.INVERSE_D2,
            date_str=self.DAY_2,
        )
        self._purchase_receipt(qty=10, price_unit=2400, inverse_rate=self.INVERSE_D2, date_str=self.DAY_2)
        product = self._product()
        self.assertEqual(product.qty_available, 20)
        self.assertAlmostEqual(product.total_value_in_currency, 30.17, places=2)
        self.assertAlmostEqual(product.standard_price_in_currency, 1.51, places=2)

    def test_delivery_does_not_change_std_price_in_currency(self):
        """Op 4: OUT con picking no-purchase. `_set_value` valúa al AVCO vigente
        (standard_price_in_currency previo al move). El AVCO en USD NO se recompute en OUTs.
        """
        self._seed_two_receipts()
        picking, move = self._delivery(qty=5, date_str=self.DAY_2)

        # Odoo 19: move.value es magnitud positiva (la dirección la da is_out).
        self.assertAlmostEqual(move.value, 8550, places=2)
        # AVCO vigente: 5 × 1.508335 ≈ 7.54
        self.assertAlmostEqual(move.value_in_currency, 7.54, places=2)

        product = self._product()
        self.assertEqual(product.qty_available, 15)
        # OUT no dispara recompute de standard_price_in_currency
        self.assertAlmostEqual(product.standard_price_in_currency, 1.51, places=2)
        self.assertAlmostEqual(product.total_value_in_currency, 22.63, places=2)

    def test_delivery_value_matches_avco_replay(self):
        """`move.value_in_currency` del OUT y el `out_value` que usa internamente el
        replay del AVCO (`out_value = qty × AVCO vigente`) son ahora el mismo cálculo,
        así que coinciden por construcción.
        """
        self._seed_two_receipts()
        product = self._product()
        avg_before = product.standard_price_in_currency

        _picking, move = self._delivery(qty=5, date_str=self.DAY_2)
        product = self._product()

        self.assertAlmostEqual(move.value_in_currency, 5 * avg_before, places=2)
        # OUT vía AVCO: total = 30.17 - 5 × avg_before ≈ 30.17 - 5 × 1.5085 ≈ 22.6275
        expected_total = 30.17 - 5 * avg_before
        self.assertAlmostEqual(product.total_value_in_currency, expected_total, places=2)

    def test_return_uses_date_rate_not_original_rate(self):
        """Op 5: devolución del cliente — picking IN sin purchase_id. La tasa del move es
        la conversión por fecha (Día 3), no la tasa histórica del move original (Día 2).
        Esto degrada el AVCO en USD.
        """
        self._seed_two_receipts()
        delivery, _delivery_move = self._delivery(qty=5, date_str=self.DAY_2)

        return_pick, return_move = self._return(delivery, qty=2, date_str=self.DAY_3)

        # 2 × 1710 = 3420 ARS; 3420 × 0.000667 ≈ 2.28 USD (rate Día 3, NO Día 2)
        self.assertAlmostEqual(return_move.value, 3420, places=2)
        self.assertAlmostEqual(return_move.value_in_currency, 2.28, places=2)

        product = self._product()
        self.assertEqual(product.qty_available, 17)
        self.assertAlmostEqual(product.total_value_in_currency, 24.91, places=2)
        # avg cae de 1.51 a ≈1.47 — divergencia documentada en TESTING.md Op 5
        self.assertAlmostEqual(product.standard_price_in_currency, 1.47, places=2)
