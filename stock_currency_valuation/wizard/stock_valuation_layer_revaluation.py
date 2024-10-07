from odoo import models


class StockValuationLayerRevaluation(models.TransientModel):
    _inherit = 'stock.valuation.layer.revaluation'

    def action_validate_revaluation(self):
        res = super().action_validate_revaluation()
        # Update the stardard price in currency in case of AVCO
        product_id = self.product_id.with_company(self.company_id)
        if product_id.categ_id.property_cost_method in ('average', 'fifo') and product_id.categ_id.valuation_currency_id:
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
        return res
