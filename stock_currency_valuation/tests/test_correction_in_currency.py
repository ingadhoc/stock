from datetime import timedelta

from .common import TestStockCurrencyValuationCommon


class TestCorrectionInCurrency(TestStockCurrencyValuationCommon):
    """In 20 a change on a past receipt replays the later outgoing moves: their amount in
    currency has to follow, or both currencies stop telling the same story."""

    def _seed(self, cost_method):
        self.category.with_company(self.company).property_cost_method = cost_method
        if cost_method == "standard":
            product = self._product()
            product.standard_price = 1000
            product.standard_price_in_currency = 1.0
        _picking, receipt = self._purchase_receipt(10, 1000, self.INVERSE_D1, self.DAY_1)
        _delivery, delivery_move = self._delivery(qty=4, date_str=self.DAY_1)
        self.assertAlmostEqual(delivery_move.value, -4000, places=2)
        self.assertAlmostEqual(delivery_move.value_in_currency, -4.0, places=2)
        return receipt, delivery_move

    def _adjust(self, receipt, value, value_in_currency):
        self.env["product.value"].create(
            {
                "move_id": receipt.id,
                "value": value,
                "value_in_currency": value_in_currency,
                "company_id": self.company.id,
            }
        )

    def test_average_replays_the_outgoing_move(self):
        receipt, delivery_move = self._seed("average")
        self._adjust(receipt, 20000, 20.0)
        self.assertAlmostEqual(delivery_move.value, -8000, places=2)
        self.assertAlmostEqual(delivery_move.value_in_currency, -8.0, places=2)
        product = self._product()
        self.assertAlmostEqual(product.standard_price_in_currency, 2.0, places=2)
        self.assertAlmostEqual(product.total_value_in_currency, 12.0, places=2)

    def test_fifo_moves_the_outgoing_move_in_proportion(self):
        receipt, delivery_move = self._seed("fifo")
        self._adjust(receipt, 20000, 20.0)
        self.assertAlmostEqual(delivery_move.value, -8000, places=2)
        # Same proportion as the company value: -4 x 8000 / 4000.
        self.assertAlmostEqual(delivery_move.value_in_currency, -8.0, places=2)

    def test_standard_reads_the_cost_in_force_at_the_move_date(self):
        _receipt, delivery_move = self._seed("standard")
        product = self._product()
        self.env["product.value"].create(
            {
                "product_id": product.id,
                "value": 3000,
                "value_in_currency": 3.0,
                "date": delivery_move.date - timedelta(seconds=1),
                "company_id": self.company.id,
            }
        )
        product._correct_inventory_valuation(delivery_move.date - timedelta(days=1))
        self.assertAlmostEqual(delivery_move.value, -12000, places=2)
        self.assertAlmostEqual(delivery_move.value_in_currency, -12.0, places=2)
