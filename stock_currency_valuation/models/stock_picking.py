from odoo import api, fields, models


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
        copy=False,
        help="If no rate is defined, the rate of the confirmation date is used.",
    )

    @api.depends("currency_rate")
    def _compute_inverse_currency_rate(self):
        for rec in self:
            rec.inverse_currency_rate = 1 / rec.currency_rate if rec.currency_rate else 0

    def _inverse_currency_rate(self):
        for rec in self:
            rec.currency_rate = 1 / rec.inverse_currency_rate if rec.inverse_currency_rate else 0

    def _compute_valuation_currency_id(self):
        for rec in self.filtered(lambda x: x.purchase_id and x.picking_type_id.code == "incoming"):
            valuation_currency_id = rec.move_ids.with_company(rec.company_id.id).mapped(
                "product_id.categ_id.valuation_currency_id"
            )
            if len(valuation_currency_id) == 1:
                self = self - rec
                rec.valuation_currency_id = valuation_currency_id.id
        self.valuation_currency_id = False
