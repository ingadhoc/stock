from collections import defaultdict

from odoo.tests import tagged

from .common import TestStockCurrencyValuationCommon


@tagged("post_install", "-at_install")
class TestClosingAmountCurrency(TestStockCurrencyValuationCommon):
    """The periodic closing entry carries the secondary amount, and keeps balancing per
    currency after the entry is split into one line per product."""

    def setUp(self):
        super().setUp()
        self.category.with_company(self.company).property_valuation = "periodic"

    def _assert_balanced_per_currency(self, entry):
        self._assert_almost(sum(entry.line_ids.mapped("balance")), 0.0)
        by_currency = defaultdict(float)
        for line in entry.line_ids:
            by_currency[line.currency_id] += line.amount_currency
        for currency, total in by_currency.items():
            self._assert_almost(total, 0.0, msg=f"The entry does not balance in {currency.name}")

    def _close(self):
        self.company.action_close_stock_valuation()
        closings = self.env["account.move"].search([("company_id", "=", self.company.id)], order="id desc", limit=1)
        return closings

    def test_closing_entry_carries_the_secondary_amount(self):
        self._purchase_receipt(4, 25000.0, self.INVERSE_D1, self.DAY_1)
        entry = self._close()

        self.assertTrue(entry, "The closing has to produce an entry.")
        in_secondary = entry.line_ids.filtered(lambda line: line.currency_id == self.secondary_currency)
        self.assertTrue(in_secondary, "The valuation lines have to be in the secondary currency.")
        self.assertTrue(all(line.amount_currency for line in in_secondary))

    def test_closing_entry_balances_per_currency(self):
        self._purchase_receipt(4, 25000.0, self.INVERSE_D1, self.DAY_1)
        entry = self._close()
        self._assert_balanced_per_currency(entry)

    def test_split_per_product_keeps_the_secondary_balance(self):
        """The entry is split into one line per product, so the secondary amount has to be
        PRORATED and not copied. Copying it would leave each product line carrying the full
        amount: the entry would still add up in company currency and not in the other one,
        which is exactly the failure this asserts against."""
        self._purchase_receipt(4, 25000.0, self.INVERSE_D1, self.DAY_1)
        second_product = self.env["product.product"].create(
            {
                "name": "Segundo producto",
                "is_storable": True,
                "categ_id": self.category.id,
                "uom_id": self.uom_unit.id,
            }
        )
        # It needs a cost, in both currencies: a product worth zero contributes no delta,
        # the split produces a SINGLE product line, and then prorating or copying the
        # secondary amount give the same result — the scenario would not exercise the
        # proration at all.
        scoped = second_product.with_company(self.company)
        scoped.standard_price = 25000.0
        scoped.standard_price_in_currency = 25.0
        # Same category, so the same valuation account: the closing line for that account
        # gets split between the two products.
        quant = (
            self.env["stock.quant"]
            .with_context(inventory_mode=True)
            .create(
                {
                    "product_id": second_product.id,
                    "location_id": self.stock_location.id,
                    "inventory_quantity": 3.0,
                }
            )
        )
        quant.action_apply_inventory()

        entry = self._close()

        self._assert_balanced_per_currency(entry)
        # The split really happened over MORE THAN ONE product, otherwise there is nothing
        # to prorate and this test measures nothing. Only the valuation leg is split —the
        # counterpart stays whole— so with N product lines an amount copied instead of
        # prorated would leave N x amount against a single -amount.
        valuation_lines = entry.line_ids.filtered(
            lambda line: line.currency_id == self.secondary_currency and line.product_id
        )
        self.assertGreater(
            len(valuation_lines),
            1,
            "The closing has to split over several products for the proration to be exercised.",
        )

    def test_account_shared_with_products_in_no_currency_stays_in_company_currency(self):
        """A valuation account holding products valued in a second currency AND products
        valued in none cannot be stated in one currency, so the closing leaves it in
        company currency instead of sharing the secondary amount among all of them.

        Without this the amount goes to products it does not belong to: measured on a
        database with demo data, of 100 belonging to a single product that product kept
        14,49 and the rest went to a dozen furniture products valued in no second currency.
        """
        self._purchase_receipt(4, 25000.0, self.INVERSE_D1, self.DAY_1)
        plain_category = self.env["product.category"].create(
            {"name": "Plain, no valuation currency", "property_cost_method": "average"}
        )
        plain_category.with_company(self.company).property_valuation = "periodic"
        # Same valuation account as the fixture's category, and no secondary currency.
        plain_category.with_company(self.company).property_stock_valuation_account_id = self.valuation_account
        plain = self.env["product.product"].create(
            {
                "name": "Producto sin moneda",
                "is_storable": True,
                "categ_id": plain_category.id,
                "uom_id": self.uom_unit.id,
            }
        )
        plain.with_company(self.company).standard_price = 3333.0
        quant = (
            self.env["stock.quant"]
            .with_context(inventory_mode=True)
            .create({"product_id": plain.id, "location_id": self.stock_location.id, "inventory_quantity": 3.0})
        )
        quant.action_apply_inventory()
        self.assertFalse(plain.with_company(self.company).valuation_currency_id)

        entry = self._close()

        self.assertTrue(entry, "The closing has to produce an entry.")
        self.assertFalse(
            entry.line_ids.filtered(lambda line: line.currency_id == self.secondary_currency),
            "A mixed valuation account has to stay in company currency.",
        )
        self._assert_balanced_per_currency(entry)

    def test_secondary_shares_add_up_to_the_cent(self):
        """Three equal shares of 100 round to 33,33 each and a cent goes missing. The
        leftover has to land on one of the lines: the entry balances in company currency
        either way, so nothing downstream would catch it and it would post unbalanced in
        the secondary currency."""
        vals = {
            "account_id": self.valuation_account.id,
            "name": "Closing",
            "debit": 300.0,
            "credit": 0.0,
            "product_id": False,
            "currency_id": self.secondary_currency.id,
            "amount_currency": 100.0,
        }
        product_vals = [self.company._get_valuation_val(vals, 100.0, False, net=300.0) for _ in range(3)]

        balanced = self.company._balance_valuation_extra_vals(vals, product_vals)

        self._assert_almost(sum(share["amount_currency"] for share in balanced), 100.0)
        for share in balanced:
            self.assertEqual(
                share["amount_currency"],
                self.secondary_currency.round(share["amount_currency"]),
                "Every share is rounded to the currency precision.",
            )
