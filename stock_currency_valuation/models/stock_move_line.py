from odoo import models, api, fields


class StockMoveLine(models.Model):

    _inherit = "stock.move.line"

    @api.model
    def _create_correction_svl(self, move, diff):
        return super(StockMoveLine, self.with_context(default_bypass_currency_valuation=True)
                     )._create_correction_svl(move=move, diff=diff)
