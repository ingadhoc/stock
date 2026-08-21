from odoo import Command
from odoo.tests import tagged

from .common import TestStockCurrencyValuationCommon


@tagged("post_install", "-at_install")
class TestMultiCompanyCurrency(TestStockCurrencyValuationCommon):
    """The valuation currency lives on the product CATEGORY and is company-dependent, so
    every backend read has to resolve it with the company of the RECORD and not with the
    active one.

    Contract of the seam ``account-multicompany-ux`` <-> ``stock-currency-valuation``:
    with multi-company UX a user can have company A selected while operating on a record
    of company B, and a company-dependent field read off the context then answers for the
    wrong company — silently, returning a number instead of failing.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_b = cls.env["res.company"].create({"name": "SCV Company B"})
        cls.env.user.company_ids = [Command.link(cls.company_b.id)]
        cls.currency_b = cls.env["res.currency"].create({"name": "SCB", "symbol": "B$", "rounding": 0.01})
        cls.env["res.currency.rate"].create(
            {
                "name": cls.DAY_1,
                "rate": cls.RATE_D1,
                "currency_id": cls.currency_b.id,
                "company_id": cls.company_b.id,
            }
        )
        # SAME category, a different valuation currency in each company.
        cls.category.with_company(cls.company_b).valuation_currency_id = cls.currency_b
        # And a different secondary cost in each one, so a crossed read is visible.
        cls.product.with_company(cls.company).standard_price_in_currency = 100.0
        cls.product.with_company(cls.company_b).standard_price_in_currency = 700.0
        cls.warehouse_b = cls.env["stock.warehouse"].search([("company_id", "=", cls.company_b.id)], limit=1)
        # Category whose valuation currency exists ONLY in company B. This is what makes
        # the divergence visible: with both companies configured, a read off the wrong one
        # still returns A currency and the amount comes out the same, so the test would
        # pass either way and prove nothing.
        cls.category_b_only = cls.env["product.category"].create(
            {"name": "SCV only in B", "property_cost_method": "average"}
        )
        cls.category_b_only.with_company(cls.company_b).valuation_currency_id = cls.currency_b
        cls.product_b_only = cls.env["product.product"].create(
            {
                "name": "Producto sólo B",
                "is_storable": True,
                "standard_price": 0.0,
                "categ_id": cls.category_b_only.id,
                "uom_id": cls.uom_unit.id,
            }
        )
        cls.product_b_only.with_company(cls.company_b).standard_price_in_currency = 700.0

    def test_valuation_currency_is_resolved_per_company(self):
        self.assertEqual(
            self.product.with_company(self.company).valuation_currency_id,
            self.secondary_currency,
        )
        self.assertEqual(
            self.product.with_company(self.company_b).valuation_currency_id,
            self.currency_b,
        )

    def test_valuation_currency_absent_in_the_active_company(self):
        """The category has a valuation currency in B and NONE in A."""
        self.assertFalse(self.product_b_only.with_company(self.company).valuation_currency_id)
        self.assertEqual(
            self.product_b_only.with_company(self.company_b).valuation_currency_id,
            self.currency_b,
        )

    def test_quant_secondary_value_uses_the_quants_company(self):
        """A quant of company B valued while company A is the active one, on a category
        whose valuation currency exists only in B.

        Reading the guard off the ambient company answers "no valuation currency" —that is
        true for A— and the quant is skipped, so its secondary value stays at zero even
        though in its own company it is worth 5 x 700. The amount does not come out wrong:
        it does not come out at all.
        """
        self.assertTrue(self.warehouse_b, "Company B needs a warehouse of its own.")
        quant = (
            self.env["stock.quant"]
            .with_company(self.company_b)
            .with_context(inventory_mode=True)
            .create(
                {
                    "product_id": self.product_b_only.id,
                    "location_id": self.warehouse_b.lot_stock_id.id,
                    "inventory_quantity": 5.0,
                }
            )
        )
        quant.action_apply_inventory()
        # Re-browsed from an env whose company is A and WITHOUT B in the context: a
        # company-dependent field resolves off the RECORDSET's context, so reading it on
        # the ``with_company(company_b)`` recordset used to create the quant would answer
        # for B either way and the test would prove nothing.
        quant_seen_from_a = self.env["stock.quant"].browse(quant.id)
        self.assertEqual(quant_seen_from_a.env.company, self.company)
        self.assertFalse(quant_seen_from_a.valuation_currency_id)
        self.assertAlmostEqual(quant_seen_from_a.secondary_value, 5.0 * 700.0)
