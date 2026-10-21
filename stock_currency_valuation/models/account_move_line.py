from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _prepare_pdiff_vals(self, layer, aml, layer_price_unit, out_qty_to_invoice, qty_to_correct):
        svl_vals_list, aml_vals_list = super()._prepare_pdiff_vals(
            layer, aml, layer_price_unit, out_qty_to_invoice, qty_to_correct
        )
        # a bill in another currency keeps the layer compute (converted at the bill date)
        if svl_vals_list and layer.quantity and layer.valuation_currency_id == aml.currency_id:
            svl_vals_list[0]["bypass_currency_valuation"] = True
            svl_vals_list[0]["value_in_currency"] = layer._get_pdiff_value_in_currency(aml, qty_to_correct)
        return svl_vals_list, aml_vals_list
