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

    def get_valuation_lines(self):
        """Take the original value in currency off the move, as the core takes ``former_cost``.

        The move already holds its value in the secondary currency, valued at the rate of its
        receipt (plus the landed costs validated before). Converting ``former_cost`` with the
        rate of this landed cost instead would value the receipt again at another rate.
        """
        lines = super().get_valuation_lines()
        moves = self.env["stock.move"].browse([vals["move_id"] for vals in lines])
        for vals, move in zip(lines, moves, strict=True):
            if move.with_company(self.company_id).valuation_currency_id:
                vals["former_cost_in_currency"] = move.value_in_currency
            else:
                vals["former_cost_in_currency"] = vals["former_cost"]
        return lines


class StockValuationAdjustmentLines(models.Model):
    _inherit = "stock.valuation.adjustment.lines"

    valuation_currency_id = fields.Many2one(
        "res.currency",
        related="cost_id.valuation_currency_id",
        store=True,
    )
    # Not computed: set by ``stock.landed.cost.get_valuation_lines`` from the move, like the
    # core's ``former_cost``. Recomputing it later would read a move that already includes
    # this landed cost.
    former_cost_in_currency = fields.Monetary(
        string="Original Value in Currency",
        currency_field="valuation_currency_id",
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
        "former_cost_in_currency",
        "additional_landed_cost",
        "final_cost",
        "valuation_currency_id",
        "cost_id.currency_rate",
        "cost_id.date",
    )
    def _compute_amounts_in_currency(self):
        """Only the additional cost is converted, with the rate of the landed cost: the
        original value is the move's own (see ``get_valuation_lines``)."""
        for line in self:
            if not line.valuation_currency_id or line.valuation_currency_id == line.currency_id:
                line.additional_landed_cost_in_currency = line.additional_landed_cost
                line.final_cost_in_currency = line.final_cost
                continue
            rate = line._get_currency_rate()
            rounding = line.valuation_currency_id.rounding
            line.additional_landed_cost_in_currency = float_round(
                line.additional_landed_cost * rate, precision_rounding=rounding
            )
            line.final_cost_in_currency = line.former_cost_in_currency + line.additional_landed_cost_in_currency
