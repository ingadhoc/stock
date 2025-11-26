from odoo import api, fields, models


class ProductValue(models.Model):
    _inherit = "product.value"

    valuation_currency_id = fields.Many2one("res.currency", compute="_compute_valuation_currency_id", store=True)
    value_in_currency = fields.Monetary(string="Value in Currency", currency_field="valuation_currency_id")

    @api.depends("company_id", "move_id", "lot_id", "product_id")
    def _compute_valuation_currency_id(self):
        for product_value in self:
            if product_value.move_id:
                product_value.valuation_currency_id = product_value.move_id.product_id.with_company(
                    product_value.company_id
                ).valuation_currency_id.id
            elif product_value.lot_id:
                product_value.valuation_currency_id = product_value.lot_id.product_id.with_company(
                    product_value.company_id
                ).valuation_currency_id.id
            elif product_value.product_id:
                product_value.valuation_currency_id = product_value.product_id.with_company(
                    product_value.company_id
                ).valuation_currency_id.id

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set default values from product's standard_price if not provided"""
        for vals in vals_list:
            # Obtener el producto según el contexto
            product = None
            if vals.get("product_id"):
                product = self.env["product.product"].browse(vals["product_id"])
            elif vals.get("lot_id"):
                lot = self.env["stock.lot"].browse(vals["lot_id"])
                product = lot.product_id
            elif vals.get("move_id"):
                move = self.env["stock.move"].browse(vals["move_id"])
                product = move.product_id

            if product:
                # Obtener la compañía
                company_id = vals.get("company_id")
                if not company_id:
                    if vals.get("move_id"):
                        company_id = self.env["stock.move"].browse(vals["move_id"]).company_id.id
                    elif vals.get("lot_id"):
                        company_id = self.env["stock.lot"].browse(vals["lot_id"]).company_id.id
                    else:
                        company_id = self.env.company.id

                company = self.env["res.company"].browse(company_id)
                product_with_company = product.with_company(company)

                # Si no está definido value, usar standard_price del producto.
                # Ojo: chequear sólo ausencia de la clave, no falsy — un 0 explícito
                # (p.ej. una corrección manual a cero vía value_manual) es un valor
                # válido y no debe pisarse con el standard_price vigente.
                if "value" not in vals:
                    vals["value"] = product_with_company.standard_price

                # Idem para value_in_currency, si el producto tiene moneda de valuación.
                if "value_in_currency" not in vals and product_with_company.valuation_currency_id:
                    vals["value_in_currency"] = product_with_company.standard_price_in_currency
        return super().create(vals_list)
