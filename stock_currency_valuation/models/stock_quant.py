from odoo import api, fields, models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    valuation_currency_id = fields.Many2one(
        related="product_id.valuation_currency_id",
    )

    secondary_value = fields.Monetary(
        currency_field="valuation_currency_id",
        compute="_compute_secondary_value",
        groups="stock.group_stock_manager",
    )

    @api.depends(
        "company_id",
        "location_id",
        "owner_id",
        "product_id",
        "quantity",
        "product_id.standard_price_in_currency",
    )
    def _compute_secondary_value(self):
        self.secondary_value = 0.0
        for quant in self:
            # The product is resolved ONCE with the quant's own company and reused for
            # both the guard and the price. The valuation currency lives on the product
            # category and is company-dependent, so reading it off the ambient company
            # —as ``quant.valuation_currency_id`` does— can disagree with the price read
            # below: with account_multicompany_ux a user can have company A selected
            # while looking at a quant of company B, and then the guard answered for A
            # and the amount for B.
            product = quant.product_id.with_company(quant.company_id)
            if not product.valuation_currency_id:
                continue
            if not quant.location_id or not quant.product_id:
                continue
            if not quant.location_id._should_be_valued() or quant._should_exclude_for_valuation():
                continue
            if quant.product_id.uom_id.is_zero(quant.quantity):
                continue
            quant.secondary_value = quant.quantity * product.standard_price_in_currency
