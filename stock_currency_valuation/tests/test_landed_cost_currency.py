from freezegun import freeze_time
from odoo import Command

from .common import TestStockCurrencyValuationCommon


class TestLandedCostCurrency(TestStockCurrencyValuationCommon):
    """Tests del landed cost en moneda secundaria — Op 2 de TESTING.md."""

    def test_lc_uses_its_own_currency_rate(self):
        """Op 2: el LC se valua con su propia tasa, no con la del picking.

        Picking en Día 1 (rate 1/1000). LC en Día 2 con rate manual 1/1200.
        El LC USD debe usar el rate del LC, y el move resultante debe quedar
        `base × rate_picking + lc × rate_lc`.
        """
        picking, move = self._purchase_receipt(
            qty=10, price_unit=1000, inverse_rate=self.INVERSE_D1, date_str=self.DAY_1
        )
        self.assertAlmostEqual(move.value, 10000, places=2)
        self.assertAlmostEqual(move.value_in_currency, 10.00, places=2)

        lc = self._landed_cost(picking=picking, amount=200, inverse_rate=self.INVERSE_D2, date_str=self.DAY_2)
        line = lc.valuation_adjustment_lines
        self.assertAlmostEqual(line._get_currency_rate(), self.RATE_D2, places=6)
        self.assertAlmostEqual(line.additional_landed_cost_in_currency, 0.17, places=2)

        # Disparidad esperada: base con tasa del picking (Día 1), LC con tasa del LC (Día 2).
        self.assertAlmostEqual(move.value, 10200, places=2)
        self.assertAlmostEqual(move.value_in_currency, 10.17, places=2)

        product = self._product()
        self.assertAlmostEqual(product.total_value_in_currency, 10.17, places=2)
        self.assertAlmostEqual(product.standard_price_in_currency, 1.02, places=2)

    def test_lc_with_rate_equal_to_picking(self):
        """Caso de control: si se setea la misma cotización en el LC que en el picking,
        no hay disparidad y el resultado es consistente (10.00 + 0.20 = 10.20).
        """
        picking, move = self._purchase_receipt(
            qty=10, price_unit=1000, inverse_rate=self.INVERSE_D1, date_str=self.DAY_1
        )
        lc = self._landed_cost(picking=picking, amount=200, inverse_rate=self.INVERSE_D1, date_str=self.DAY_2)
        line = lc.valuation_adjustment_lines
        self.assertAlmostEqual(line._get_currency_rate(), self.RATE_D1, places=6)
        self.assertAlmostEqual(line.additional_landed_cost_in_currency, 0.20, places=2)
        self.assertAlmostEqual(move.value_in_currency, 10.20, places=2)

        product = self._product()
        self.assertAlmostEqual(product.total_value_in_currency, 10.20, places=2)
        self.assertAlmostEqual(product.standard_price_in_currency, 1.02, places=2)

    def test_lc_falls_back_to_date_rate_when_unset(self):
        """Si no se setea cotización en el LC, `_get_currency_rate` cae a la
        tasa de la fecha en `res.currency.rate` (Día 2 → 1/1200).
        """
        picking, _move = self._purchase_receipt(
            qty=10, price_unit=1000, inverse_rate=self.INVERSE_D1, date_str=self.DAY_1
        )
        # No seteamos `inverse_currency_rate` en el LC: se fuerza el fallback a la tasa de la fecha.
        lc = self._landed_cost(picking=picking, amount=200, inverse_rate=0, date_str=self.DAY_2)
        line = lc.valuation_adjustment_lines
        self.assertAlmostEqual(line._get_currency_rate(), self.RATE_D2, places=6)
        self.assertAlmostEqual(line.additional_landed_cost_in_currency, 0.17, places=2)

    def test_amounts_in_currency_recompute_when_date_changes(self):
        """Sin cotización manual, `_get_currency_rate` usa `cost_id.date` como fallback
        (línea 84). `cost_id.date` no estaba en el `@api.depends` de
        `_compute_amounts_in_currency`, así que cambiar la fecha en borrador (antes de
        validar) no recomputaba el campo *_in_currency guardado, que quedaba con la
        tasa vieja.
        """
        picking, _move = self._purchase_receipt(
            qty=10, price_unit=1000, inverse_rate=self.INVERSE_D1, date_str=self.DAY_1
        )
        with freeze_time(self.DAY_2):
            lc = self.env["stock.landed.cost"].create(
                {
                    "picking_ids": [Command.set(picking.ids)],
                    "account_journal_id": self.lc_journal.id,
                    "date": self.DAY_2,
                    "cost_lines": [
                        Command.create(
                            {
                                "product_id": self.lc_service.id,
                                "name": "LC line",
                                "price_unit": 200,
                                "split_method": "by_quantity",
                            }
                        )
                    ],
                }
            )
            lc.compute_landed_cost()
            line = lc.valuation_adjustment_lines
            self.assertAlmostEqual(line.additional_landed_cost_in_currency, 200 * self.RATE_D2, places=2)

            # Cambiar la fecha a Día 3 en borrador, sin recomputar manualmente ni tocar
            # former_cost/additional_landed_cost/final_cost.
            lc.date = self.DAY_3
            self.assertAlmostEqual(line.additional_landed_cost_in_currency, 200 * self.RATE_D3, places=2)

    def test_lc_on_out_move_does_not_pollute_value_in_currency(self):
        """Un landed cost puede linkearse a un move OUT: `stock.landed.cost.picking_ids`
        no restringe por dirección (ver dominio de la vista del core, que acepta
        `move_ids.is_in` u `move_ids.is_out`). El core nunca incorpora ese costo a
        `move.value` en OUT (`_get_value_from_extra` sólo se usa para IN), así que
        `value_in_currency` tampoco debe incluirlo — si lo hiciera, rompería el
        invariante "OUT valúa siempre al AVCO vigente" (ver TESTING.md Op 4/6/7).
        """
        self._purchase_receipt(qty=10, price_unit=1000, inverse_rate=self.INVERSE_D1, date_str=self.DAY_1)
        product = self._product()
        avg_before = product.standard_price_in_currency
        self.assertAlmostEqual(avg_before, 1.00, places=2)

        delivery, move = self._delivery(qty=4, date_str=self.DAY_1)
        expected_value_in_currency = 4 * avg_before
        self.assertAlmostEqual(move.value, 4000, places=2)
        self.assertAlmostEqual(move.value_in_currency, expected_value_in_currency, places=2)

        # LC de 200 ARS sobre el picking de la entrega (rate Día 1 -> 0.20 USD si se sumara).
        self._landed_cost(picking=delivery, amount=200, inverse_rate=self.INVERSE_D1, date_str=self.DAY_1)

        # move.value en ARS no cambia (paridad con el core) y value_in_currency tampoco.
        self.assertAlmostEqual(move.value, 4000, places=2)
        self.assertAlmostEqual(move.value_in_currency, expected_value_in_currency, places=2)

        product = self._product()
        self.assertAlmostEqual(product.total_value_in_currency, 10.00 - expected_value_in_currency, places=2)
        self.assertAlmostEqual(product.standard_price_in_currency, avg_before, places=2)
