from odoo.tests import tagged

from .common import TestStockCurrencyValuationCommon


@tagged("post_install", "-at_install")
class TestInventoryValueInCurrency(TestStockCurrencyValuationCommon):
    """``_get_inventory_value_in_currency``: what a move contributes to the valuation in
    the secondary currency. Twin of the company-currency criterion in ``stock_account_ux``,
    and the single home both the manual valuation wizard and the report's breakdown of the
    variation read."""

    def test_contribution_is_the_moves_secondary_value(self):
        _picking, move = self._purchase_receipt(4, 25.0, self.INVERSE_D1, self.DAY_1)
        self.assertTrue(move.value_in_currency)
        self._assert_almost(move._get_inventory_value_in_currency(), move.value_in_currency)

    def test_contribution_is_the_moves_own_value_not_the_current_average(self):
        """With two receipts at different rates the AVCO in the secondary currency is a
        blend, so a move's own value is no longer ``quantity x current average``.

        The contribution has to be what THIS move was worth, not a recomputation at today's
        average: the report's variation and the wizard book past moves, and recomputing
        them would restate history every time the average moves. This is the case that
        tells the two implementations apart — where the rate never changes they agree.
        """
        # Amounts big enough for the gap between the two implementations to be
        # unambiguous: with 25 per unit the secondary values land around 0.1 and the
        # difference falls within the rounding of the comparison.
        _p1, first = self._purchase_receipt(4, 25000.0, self.INVERSE_D1, self.DAY_1)
        own_value = first.value_in_currency
        self.assertTrue(own_value)

        # Second receipt at another rate: the average in the secondary currency shifts.
        self._purchase_receipt(4, 25000.0, self.INVERSE_D3, self.DAY_3)
        average_now = self._product().with_company(self.company).standard_price_in_currency
        recomputed = first._get_valued_qty() * average_now
        self.assertNotAlmostEqual(
            recomputed,
            own_value,
            places=2,
            msg="The blended average has to differ from the move's own value, or this proves nothing.",
        )

        self._assert_almost(first._get_inventory_value_in_currency(), own_value)

    def test_contribution_is_zero_without_a_secondary_currency(self):
        no_currency_category = self.env["product.category"].create(
            {"name": "SCV no currency", "property_cost_method": "average"}
        )
        product = self.env["product.product"].create(
            {
                "name": "Producto sin moneda",
                "is_storable": True,
                "categ_id": no_currency_category.id,
                "uom_id": self.uom_unit.id,
            }
        )
        self.assertFalse(product.with_company(self.company).valuation_currency_id)
        move = self.env["stock.move"].create(
            {
                "product_id": product.id,
                "product_uom_qty": 1.0,
                "product_uom": self.uom_unit.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
            }
        )
        self._assert_almost(move._get_inventory_value_in_currency(), 0.0)
