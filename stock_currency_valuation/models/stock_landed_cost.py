from odoo import api, fields, models
from odoo.tools import float_round


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


class StockValuationAdjustmentLines(models.Model):
    _inherit = "stock.valuation.adjustment.lines"

    # The product's own currency: a landed cost may also reach products valued in none
    valuation_currency_id = fields.Many2one(
        "res.currency",
        compute="_compute_valuation_currency_id",
        store=True,
    )
    former_cost_in_currency = fields.Monetary(
        string="Original Value in Currency",
        currency_field="valuation_currency_id",
        compute="_compute_amounts_in_currency",
        store=True,
    )
    additional_landed_cost_in_currency = fields.Monetary(
        string="Additional Landed Cost in Currency",
        currency_field="valuation_currency_id",
        compute="_compute_amounts_in_currency",
        store=True,
    )
    final_cost_in_currency = fields.Monetary(
        string="New Value in Currency",
        currency_field="valuation_currency_id",
        compute="_compute_amounts_in_currency",
        store=True,
    )

    @api.depends("product_id.categ_id", "cost_id.company_id")
    def _compute_valuation_currency_id(self):
        for line in self:
            line.valuation_currency_id = line.product_id.with_company(line.cost_id.company_id).valuation_currency_id

    def _get_currency_rate(self):
        """Return the effective rate to convert from company currency to valuation currency.

        If a manual rate is set on the landed cost, use it.
        Otherwise convert using today's rate.
        """
        self.ensure_one()
        if self.cost_id.currency_rate:
            return self.cost_id.currency_rate
        if not self.valuation_currency_id or self.valuation_currency_id == self.currency_id:
            return 1.0
        # Sin cotización manual: usar la tasa de la fecha del landed cost (fecha de
        # confirmación), no la de "hoy". De lo contrario, al recomputar más tarde se
        # tomaría la última tasa vigente en lugar de la del momento del ajuste.
        date = self.cost_id.date or fields.Date.context_today(self)
        rate = self.currency_id._get_conversion_rate(
            from_currency=self.currency_id,
            to_currency=self.valuation_currency_id,
            company=self.cost_id.company_id,
            date=date,
        )
        return rate

    @api.depends(
        "former_cost",
        "additional_landed_cost",
        "final_cost",
        "valuation_currency_id",
        "cost_id.currency_rate",
        "cost_id.date",
        "cost_id.state",
        "move_id.value_in_currency",
    )
    def _compute_amounts_in_currency(self):
        to_convert = self.filtered(lambda line: line.valuation_currency_id)
        for line in self - to_convert:
            line.former_cost_in_currency = 0
            line.additional_landed_cost_in_currency = 0
            line.final_cost_in_currency = 0
        for line in to_convert:
            rate = line._get_currency_rate()
            line.additional_landed_cost_in_currency = float_round(
                line.additional_landed_cost * rate, precision_rounding=line.valuation_currency_id.rounding
            )
        # Same criterion as the core's former_cost (the move's value with no landed cost):
        # the move's value in currency, at the receipt's own rate, minus the landed costs
        # already applied to it, this one included once validated.
        landed_costs_by_move = to_convert.move_id.sudo()._get_landed_cost()
        for line in to_convert:
            applied = landed_costs_by_move.get(line.move_id, self.browse())
            line.former_cost_in_currency = line.move_id.value_in_currency - sum(
                applied.mapped("additional_landed_cost_in_currency")
            )
            line.final_cost_in_currency = line.former_cost_in_currency + line.additional_landed_cost_in_currency
