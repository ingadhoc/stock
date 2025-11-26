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
            if not quant.valuation_currency_id:
                continue
            if not quant.location_id or not quant.product_id:
                continue
            if not quant.location_id._should_be_valued() or quant._should_exclude_for_valuation():
                continue
            if quant.product_id.uom_id.is_zero(quant.quantity):
                continue
            secondary_price = quant.product_id.with_company(quant.company_id).standard_price_in_currency
            quant.secondary_value = quant.quantity * secondary_price
