from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _prepare_pdiff_vals(self, layer, aml, layer_price_unit, out_qty_to_invoice, qty_to_correct):
        svl_vals_list, aml_vals_list = super()._prepare_pdiff_vals(
            layer, aml, layer_price_unit, out_qty_to_invoice, qty_to_correct
        )
        if svl_vals_list:
            svl_vals_list[0]["pdiff_quantity"] = qty_to_correct
        return svl_vals_list, aml_vals_list
