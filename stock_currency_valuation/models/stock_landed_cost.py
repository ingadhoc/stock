from odoo import api, fields, models


class StockLandedCost(models.Model):
    _inherit = "stock.landed.cost"

    valuation_currency_id = fields.Many2one(
        "res.currency",
        string="Secondary Currency Valuation",
        compute="_compute_valuation_currency_id",
        help="If no rate is defined, the rate of the confirmation date is used.",
    )
    inverse_currency_rate = fields.Float(
        string="Cotizacion",
        compute="_compute_inverse_currency_rate",
        inverse="_inverse_currency_rate",
    )
    currency_rate = fields.Float(
        digits=0,
        copy=False,
    )

    @api.depends("currency_rate")
    def _compute_inverse_currency_rate(self):
        for rec in self:
            rec.inverse_currency_rate = 1 / rec.currency_rate if rec.currency_rate else 0

    def _inverse_currency_rate(self):
        for rec in self:
            rec.currency_rate = 1 / rec.inverse_currency_rate if rec.inverse_currency_rate else 0

    @api.depends("picking_ids")
    def _compute_valuation_currency_id(self):
        for rec in self:
            valuation_currency_id = rec.picking_ids.with_company(rec.company_id.id).mapped("valuation_currency_id")
            if len(valuation_currency_id) == 1:
                rec.valuation_currency_id = valuation_currency_id.id
            else:
                rec.valuation_currency_id = False


class AdjustmentLines(models.Model):
    _inherit = "stock.valuation.adjustment.lines"

    def _create_accounting_entries(self, move, qty_out):
        AccountMoveLine = super()._create_accounting_entries(move, qty_out)
        amount = AccountMoveLine[0][2].get("debit", 0) or AccountMoveLine[0][2].get("credit", 0) * -1
        if self.product_id.categ_id.valuation_currency_id and amount:
            if self.cost_id.currency_rate:
                value_in_currency = amount * self.cost_id.currency_rate
            else:
                value_in_currency = self.cost_id.currency_id._convert(
                    from_amount=amount,
                    to_currency=self.product_id.categ_id.valuation_currency_id,
                    company=self.cost_id.company_id,
                    date=self.create_date,
                )
            AccountMoveLine[0][2].update(
                {"currency_id": self.product_id.categ_id.valuation_currency_id.id, "amount_currency": value_in_currency}
            )
            AccountMoveLine[1][2].update(
                {
                    "currency_id": self.product_id.categ_id.valuation_currency_id.id,
                    "amount_currency": value_in_currency * -1,
                }
            )
        return AccountMoveLine
