from odoo import api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    valuation_currency_id = fields.Many2one(
        "res.currency",
        string="Secondary Currency Valuation",
        compute="_compute_valuation_currency_id",
    )
    inverse_currency_rate = fields.Float(
        string="Cotizacion",
        compute="_compute_inverse_currency_rate",
        inverse="_inverse_currency_rate",
        help="If no rate is defined, the rate of the confirmation date is used.",
    )
    currency_rate = fields.Float(
        digits=0,
        compute="_compute_currency_rate",
        copy=False,
        store=True,
        help="If no rate is defined, the rate of the confirmation date is used.",
    )

    def button_validate(self):
        for rec in self:
            if (
                rec.valuation_currency_id
                and self.valuation_currency_id in rec.mapped("move_ids.purchase_line_id.order_id.currency_id")
                and rec.currency_rate == 0
            ):
                raise UserError(
                    """You cannot validate a picking with a zero currency rate.
                    The purchase already has an invoice with a determined rate;
                    we suggest reviewing it and applying the corresponding rate."""
                )
        return super().button_validate()

    @api.depends("currency_rate")
    def _compute_inverse_currency_rate(self):
        for rec in self:
            rec.inverse_currency_rate = 1 / rec.currency_rate if rec.currency_rate else 0

    def _inverse_currency_rate(self):
        for rec in self:
            rec.currency_rate = 1 / rec.inverse_currency_rate if rec.inverse_currency_rate else 0

    @api.depends("valuation_currency_id", "move_ids.purchase_line_id.invoice_lines.parent_state")
    def _compute_currency_rate(self):
        for rec in self:
            if (
                not rec.currency_rate
                and rec.state not in ["cancel", "done"]
                and rec.valuation_currency_id in rec.mapped("move_ids.purchase_line_id.order_id.currency_id")
                and rec.mapped("move_ids.purchase_line_id.invoice_lines")
            ):
                invoice_lines = rec.mapped('move_ids.purchase_line_id.invoice_lines').filtered(lambda line: line.parent_state == 'posted')
                if invoice_lines:
                    rec.currency_rate = invoice_lines[:-1].move_id.invoice_currency_rate

    def _compute_valuation_currency_id(self):
        for rec in self.filtered(lambda x: x.purchase_id and x.picking_type_id.code == "incoming"):
            valuation_currency_id = rec.move_ids.with_company(rec.company_id.id).mapped(
                "product_id.categ_id.valuation_currency_id"
            )
            if len(valuation_currency_id) == 1:
                self = self - rec
                rec.valuation_currency_id = valuation_currency_id.id
        self.valuation_currency_id = False
