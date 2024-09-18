from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero


class StockValuationLayerRevaluation(models.TransientModel):
    _inherit = 'stock.valuation.layer.revaluation'

    def action_validate_revaluation(self):
        product_id = self.product_id.with_company(self.company_id)
        if product_id.categ_id.property_cost_method in ('average', 'fifo') and product_id.categ_id.valuation_currency_id:
            # Update the stardard price in currency in case of AVCO
            # Para actualizar el costo en currency vuelvo a calcular el valor en moneda
            # Si bien hago dos veces el calculo (en el layer y aqui) esto es mas
            # sencillo que obtener el ultimo layer y agregar el valor.
            value_in_currency = self.currency_id._convert(
                from_amount=self.added_value,
                to_currency=product_id.categ_id.valuation_currency_id,
                company=self.company_id,
                date=self.create_date,
            )
            product_id.with_context(disable_auto_svl=True).standard_price_in_currency += value_in_currency / self.current_quantity_svl
            res = super(StockValuationLayerRevaluation, self.with_context(
                revaluation_force_currency=product_id.categ_id.valuation_currency_id,
                revaluation_value_in_currency=value_in_currency
                )).action_validate_revaluation()
            return res
        return super().action_validate_revaluation()
