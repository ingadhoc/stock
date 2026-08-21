from freezegun import freeze_time
from odoo import fields

from .common import TestStockCurrencyValuationCommon


class TestReplenishmentCostAverageInCurrency(TestStockCurrencyValuationCommon):
    """replenishment_cost_type = 'average_in_currency': convierte
    standard_price_in_currency (moneda de valuación de la categoría) a la
    moneda del producto usando fields.Date.today().

    Regresión: la conversión usaba `fields.date.today()` (minúscula), que no
    existe en odoo.fields y rompía con AttributeError apenas se leía
    replenishment_cost/replenishment_base_cost_on_currency.
    """

    def setUp(self):
        super().setUp()
        self.template = self.product.product_tmpl_id.with_company(self.company)
        self.template.replenishment_cost_type = "average_in_currency"

    def test_average_in_currency_converts_using_valuation_currency_rate(self):
        self._product().standard_price_in_currency = 1000.0

        with freeze_time(self.DAY_1):
            self.template.invalidate_recordset(["replenishment_cost", "replenishment_base_cost_on_currency"])
            expected = self.secondary_currency._convert(
                from_amount=1000.0,
                to_currency=self.template.currency_id,
                company=self.company,
                date=fields.Date.today(),
            )
            self._assert_almost(self.template.replenishment_base_cost_on_currency, expected)
            self._assert_almost(self.template.replenishment_cost, expected)

        # Cambia la cotización (Día 2): el costo de reposición debe seguirla.
        with freeze_time(self.DAY_2):
            self.template.invalidate_recordset(["replenishment_cost", "replenishment_base_cost_on_currency"])
            expected_d2 = self.secondary_currency._convert(
                from_amount=1000.0,
                to_currency=self.template.currency_id,
                company=self.company,
                date=fields.Date.today(),
            )
            self.assertNotAlmostEqual(expected, expected_d2, places=2)
            self._assert_almost(self.template.replenishment_base_cost_on_currency, expected_d2)
            self._assert_almost(self.template.replenishment_cost, expected_d2)

    def test_average_in_currency_applies_replenishment_cost_rule_on_converted_amount(self):
        rule = self.env["product.replenishment_cost.rule"].create(
            {
                "name": "Markup SCV",
                "item_ids": [
                    (0, 0, {"name": "Markup", "percentage_amount": 10.0, "fixed_amount": 5.0}),
                ],
            }
        )
        self.template.replenishment_cost_rule_id = rule
        self._product().standard_price_in_currency = 1000.0

        with freeze_time(self.DAY_1):
            self.template.invalidate_recordset(["replenishment_cost", "replenishment_base_cost_on_currency"])
            base_cost = self.secondary_currency._convert(
                from_amount=1000.0,
                to_currency=self.template.currency_id,
                company=self.company,
                date=fields.Date.today(),
            )
            expected_cost = base_cost * 1.10 + 5.0

            self._assert_almost(self.template.replenishment_base_cost_on_currency, base_cost)
            self._assert_almost(self.template.replenishment_cost, expected_cost)
