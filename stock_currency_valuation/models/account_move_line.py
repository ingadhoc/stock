from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _prepare_pdiff_vals(self, layer, aml, layer_price_unit, out_qty_to_invoice, qty_to_correct):
        svl_vals_list, aml_vals_list = super()._prepare_pdiff_vals(
            layer, aml, layer_price_unit, out_qty_to_invoice, qty_to_correct
        )
        valuation_currency_id = self.product_id.with_company(self.company_id.id).categ_id.valuation_currency_id
        use_valuation_currency = valuation_currency_id == self.currency_id == self.purchase_line_id.currency_id
        if use_valuation_currency:
            # TODO pueden ser diferentes unidades de media
            svl_vals_list[0]["bypass_currency_valuation"] = True
            svl_vals_list[0]["value_in_currency"] = (
                self.price_total - self.purchase_line_id.price_total / self.purchase_line_id.product_qty * self.quantity
            )
        return svl_vals_list, aml_vals_list
