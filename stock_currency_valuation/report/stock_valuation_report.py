from odoo import models


class StockValuationReport(models.AbstractModel):
    _inherit = "stock_account.stock.valuation.report"

    def _is_revaluation(self, product_value):
        """Also count an adjustment that only moved the amount in the SECONDARY currency.

        The base criterion is the delta in company currency, which is the right one for a
        module that knows of no other currency. Here a move's valuation carries two
        amounts, so an adjustment that changed only the secondary one DID change the
        move's valuation: leaving that move in the Stock Moves component while its
        adjustment also lands in the Product Value remainder would count its secondary
        value twice.

        Criterion agreed for the valuation flow (task 64440, clarification Q2): an
        adjustment counts as a revaluation when it moved the value in EITHER currency. It
        only has content because the secondary amount now actually reaches the move (see
        ``stock.move._get_manual_value_in_currency``); while it did not, an adjustment of
        this kind moved nothing at all.
        """
        if super()._is_revaluation(product_value):
            return True
        currency = product_value.valuation_currency_id
        return bool(currency) and not currency.is_zero(product_value.delta_in_currency)
