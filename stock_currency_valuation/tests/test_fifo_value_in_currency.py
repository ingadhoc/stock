from freezegun import freeze_time
from odoo.tests import tagged

from .common import TestStockCurrencyValuationCommon


@tagged("post_install", "-at_install")
class TestFifoValueInCurrency(TestStockCurrencyValuationCommon):
    """FIFO products are shared across companies, so ``product.company_id`` is empty and the
    conversion to the secondary currency has to fall back to the environment company.

    ``res.currency._convert`` starts with ``self, to_currency = self or to_currency, to_currency
    or self``: called on an empty currency it takes the TARGET as source, gets rate 1 and returns
    the company-currency amount untouched. The whole suite valued in a second currency used
    ``average``, so nothing exercised this path.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category.with_company(cls.company).property_cost_method = "fifo"

    def test_shared_product_is_converted_at_the_rate_not_copied(self):
        self.assertFalse(
            self.product.company_id,
            "The product has to be shared, or the empty company_id this guards against never happens.",
        )

        self._purchase_receipt(4, 25000.0, self.INVERSE_D1, self.DAY_1)

        # The conversion is dated with today(), so the assertion only holds under the same date.
        with freeze_time(self.DAY_1):
            product = self._product()
            product.invalidate_recordset(["avg_cost_in_currency", "total_value_in_currency"])
            avg_cost = product.avg_cost_in_currency
            total_value = product.total_value_in_currency
            self._assert_almost(product.standard_price_in_currency, 25.0)

        # 4 x 25000 ARS at 1/1000 is 100 SCV. Without the fallback both came back in ARS.
        self._assert_almost(total_value, 100.0)
        self._assert_almost(avg_cost, 25.0)
        self.assertNotAlmostEqual(
            total_value,
            100000.0,
            places=2,
            msg="The secondary value is the company-currency amount copied verbatim: rate 1 was applied.",
        )

    def test_layers_keep_their_own_value_in_currency(self):
        self._purchase_receipt(10, 1000.0, 1000.0, self.DAY_1)
        self._purchase_receipt(10, 1300.0, 1300.0, self.DAY_2)

        # Today's rate (1500) differs from both receipts: nothing below may depend on it.
        with freeze_time(self.DAY_3):
            product = self._product()
            product.invalidate_recordset(["avg_cost_in_currency", "total_value_in_currency"])
            self._assert_almost(product.standard_price_in_currency, 1.0)
            self._assert_almost(product.total_value_in_currency, 20.0)

            _picking, delivery = self._delivery(15, self.DAY_3)

            # The whole first layer (USD 10) plus 5 units of the second one (USD 5).
            self._assert_almost(delivery.value, 16500.0)
            self._assert_almost(delivery.value_in_currency, 15.0)

            product.invalidate_recordset(["avg_cost_in_currency", "total_value_in_currency"])
            self._assert_almost(product.total_value_in_currency, 5.0)
            self._assert_almost(product.avg_cost_in_currency, 1.0)
            self._assert_almost(product.standard_price_in_currency, 1.0)

    def test_inventory_decrease_consumes_the_oldest_layer(self):
        self._purchase_receipt(10, 1000.0, 1000.0, self.DAY_1)
        self._purchase_receipt(10, 2600.0, 1300.0, self.DAY_2)

        with freeze_time(self.DAY_3):
            _quant, move = self._inventory_adjustment(19, self.DAY_3)

        self._assert_almost(move.value, 1000.0)
        self._assert_almost(move.value_in_currency, 1.0)
