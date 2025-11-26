from .common import TestStockCurrencyValuationCommon


class TestCombinedWalkthrough(TestStockCurrencyValuationCommon):
    """Walkthrough numérico Op 1 → Op 7 según TESTING.md.

    Test maestro de regresión: cubre desde la recepción de compra hasta los ajustes
    de inventario sin picking (Op 6 / Op 7), valuados al AVCO en moneda secundaria.
    """

    def _op1_purchase_receipt_day_1(self):
        # Recepción de compra 1: +10 unid @ 1000 ARS, rate Día 1 (1/1000).
        picking, move = self._purchase_receipt(
            qty=10, price_unit=1000, inverse_rate=self.INVERSE_D1, date_str=self.DAY_1
        )
        self.assertAlmostEqual(picking.currency_rate, self.RATE_D1, places=6)
        self.assertAlmostEqual(move.value, 10000, places=2)
        self.assertAlmostEqual(move.value_in_currency, 10.00, places=2)

        product = self._product()
        self.assertEqual(product.qty_available, 10)
        self.assertAlmostEqual(product.total_value_in_currency, 10.00, places=2)
        self.assertAlmostEqual(product.avg_cost_in_currency, 1.00, places=2)
        self.assertAlmostEqual(product.standard_price, 1000, places=2)
        self.assertAlmostEqual(product.standard_price_in_currency, 1.00, places=2)
        return picking

    def _op2_landed_cost_day_2(self, picking_op1):
        # Landed cost 200 ARS sobre Op 1, rate Día 2 (1/1200).
        lc = self._landed_cost(picking=picking_op1, amount=200, inverse_rate=self.INVERSE_D2, date_str=self.DAY_2)
        self.assertAlmostEqual(lc.currency_rate, self.RATE_D2, places=6)

        # Valuación del ajuste: usa la tasa del LC (Día 2), no la del picking (Día 1).
        line = lc.valuation_adjustment_lines
        self.assertEqual(len(line), 1)
        self.assertAlmostEqual(line.additional_landed_cost, 200, places=2)
        self.assertAlmostEqual(line._get_currency_rate(), self.RATE_D2, places=6)
        self.assertAlmostEqual(line.additional_landed_cost_in_currency, 0.17, places=2)

        # Move de la Op 1 después del LC: base con tasa Día 1, LC con tasa Día 2.
        move = picking_op1.move_ids
        self.assertAlmostEqual(move.value, 10200, places=2)
        # base = 10000 × 0.001 = 10.00 ; lc = 200 × 0.000833 ≈ 0.17 ; total ≈ 10.17
        self.assertAlmostEqual(move.value_in_currency, 10.17, places=2)

        product = self._product()
        self.assertAlmostEqual(product.total_value_in_currency, 10.17, places=2)
        self.assertAlmostEqual(product.standard_price, 1020, places=2)
        self.assertAlmostEqual(product.standard_price_in_currency, 1.02, places=2)
        return lc

    def _op3_purchase_receipt_day_2(self):
        # Recepción de compra 2: +10 @ 2400 ARS, rate Día 2 (1/1200).
        picking, move = self._purchase_receipt(
            qty=10, price_unit=2400, inverse_rate=self.INVERSE_D2, date_str=self.DAY_2
        )
        self.assertAlmostEqual(move.value, 24000, places=2)
        self.assertAlmostEqual(move.value_in_currency, 20.00, places=2)

        product = self._product()
        self.assertEqual(product.qty_available, 20)
        self.assertAlmostEqual(product.total_value_in_currency, 30.17, places=2)
        self.assertAlmostEqual(product.standard_price, 1710, places=0)
        self.assertAlmostEqual(product.standard_price_in_currency, 1.51, places=2)
        return picking

    def _op4_delivery_day_2(self):
        # Entrega a cliente: -5 unid. OUT: se valúa al AVCO USD vigente (1.508335 × 5 ≈ 7.54).
        picking, move = self._delivery(qty=5, date_str=self.DAY_2)
        # Odoo 19: move.value es magnitud positiva (la dirección la da is_out).
        self.assertAlmostEqual(move.value, 8550, places=2)
        self.assertAlmostEqual(move.value_in_currency, 7.54, places=2)

        product = self._product()
        self.assertEqual(product.qty_available, 15)
        self.assertAlmostEqual(product.total_value_in_currency, 22.63, places=2)
        # OUT no recompute std_price_in_currency
        self.assertAlmostEqual(product.standard_price_in_currency, 1.51, places=2)
        return picking

    def _op5_return_day_3(self, op4_picking):
        # Devolución de 2 unid del picking de Op 4, en fecha Día 3 (rate 1/1500).
        return_pick, move = self._return(op4_picking, qty=2, date_str=self.DAY_3)
        self.assertAlmostEqual(move.value, 3420, places=2)
        # 3420 × 0.000667 ≈ 2.28 USD (conversión por fecha, no espejo de la entrega)
        self.assertAlmostEqual(move.value_in_currency, 2.28, places=2)

        product = self._product()
        self.assertEqual(product.qty_available, 17)
        self.assertAlmostEqual(product.total_value_in_currency, 24.91, places=2)
        self.assertAlmostEqual(product.standard_price_in_currency, 1.47, places=2)
        return return_pick

    def _op6_inventory_adjustment_plus3_day_3(self):
        # Ajuste +3 (17 → 20) sin picking. Genera move IN con value_in_currency.
        _quant, move = self._inventory_adjustment(new_qty=20, date_str=self.DAY_3)
        self.assertAlmostEqual(move.value, 5130, places=2)
        # Rama "sin picking" de _set_value: +qty × AVCO USD del momento ≈ 4.40
        self.assertAlmostEqual(move.value_in_currency, 4.40, places=2)
        product = self._product()
        self.assertEqual(product.qty_available, 20)
        # 29.31 (no 29.30): value_in_currency se almacena con el redondeo de la moneda
        # (0.01), así que el ajuste guarda 4.40 y el replay acumula ese redondeo.
        self.assertAlmostEqual(product.total_value_in_currency, 29.31, places=2)
        self.assertAlmostEqual(product.standard_price_in_currency, 1.47, places=2)

    def _op7_inventory_adjustment_minus2_day_3(self):
        # Ajuste -2 (20 → 18) sin picking. Genera move OUT con value_in_currency.
        _quant, move = self._inventory_adjustment(new_qty=18, date_str=self.DAY_3)
        # Odoo 19: move.value es magnitud positiva (la dirección la da is_out).
        self.assertAlmostEqual(move.value, 3420, places=2)
        # Rama "sin picking" de _set_value: qty × AVCO USD del momento ≈ 2.93 (positivo).
        self.assertAlmostEqual(move.value_in_currency, 2.93, places=2)
        product = self._product()
        self.assertEqual(product.qty_available, 18)
        # 26.38 (no 26.37) por el mismo redondeo acumulado de Op 6.
        self.assertAlmostEqual(product.total_value_in_currency, 26.38, places=2)
        self.assertAlmostEqual(product.standard_price_in_currency, 1.47, places=2)

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_walkthrough_op_1_to_5(self):
        """Op 1 → Op 5: la parte del walkthrough que pasa con el código actual."""
        picking_op1 = self._op1_purchase_receipt_day_1()
        self._op2_landed_cost_day_2(picking_op1)
        self._op3_purchase_receipt_day_2()
        op4 = self._op4_delivery_day_2()
        self._op5_return_day_3(op4)

    def test_walkthrough_full_op_1_to_7(self):
        """Op 1 → Op 7. La rama 'sin picking' de `stock.move._set_value` valúa los
        ajustes de inventario al AVCO en moneda (ver Op 6 y Op 7 en TESTING.md).
        """
        picking_op1 = self._op1_purchase_receipt_day_1()
        self._op2_landed_cost_day_2(picking_op1)
        self._op3_purchase_receipt_day_2()
        op4 = self._op4_delivery_day_2()
        self._op5_return_day_3(op4)
        self._op6_inventory_adjustment_plus3_day_3()
        self._op7_inventory_adjustment_minus2_day_3()
