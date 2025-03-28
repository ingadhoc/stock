from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero


class StockValuationLayerRevaluation(models.TransientModel):
    _inherit = 'stock.valuation.layer.revaluation'

    show_added_value_in_currency = fields.Boolean(compute="_compute_show_added_value_in_currency",)
    valuation_currency_id = fields.Many2one(
        'res.currency',
        string='Secondary Currency Valuation',
        compute="_compute_valuation_currency_id"
    )
    added_value_in_currency = fields.Monetary(
        "Added value in currency",
        compute="_compute_added_value_in_currency",
        store=True,
        readonly=False,
        #currency_field=valuation_currency_id,
    )
    new_value_in_currency = fields.Monetary("New value in currency", compute='_compute_new_value_in_currency')
    new_value_in_currency_by_qty = fields.Monetary("New value in currency by quantity", compute='_compute_new_value')


    @api.depends('product_id', 'company_id')
    def _compute_valuation_currency_id(self):
        for rec in self:
            product_id = rec.product_id.with_company(rec.company_id)
            rec.valuation_currency_id = product_id.categ_id.valuation_currency_id

    @api.depends('product_id', 'company_id')
    def _compute_show_added_value_in_currency(self):
        for rec in self:
            product_id = rec.product_id.with_company(rec.company_id)
            rec.show_added_value_in_currency = product_id.categ_id.property_cost_method in ('average', 'fifo') \
                and product_id.categ_id.valuation_currency_id

    @api.depends('added_value', 'valuation_currency_id')
    def _compute_added_value_in_currency(self):
        for rec in self:
            product_id = rec.product_id.with_company(rec.company_id)
            if product_id.categ_id.property_cost_method in ('average', 'fifo') and product_id.categ_id.valuation_currency_id:
                # Update the stardard price in currency in case of AVCO
                # Para actualizar el costo en currency vuelvo a calcular el valor en moneda
                # Si bien hago dos veces el calculo (en el layer y aqui) esto es mas
                # sencillo que obtener el ultimo layer y agregar el valor.
                rec.added_value_in_currency = rec.currency_id._convert(
                    from_amount=rec.added_value,
                    to_currency=product_id.categ_id.valuation_currency_id,
                    company=rec.company_id,
                    date=fields.Date.today(),
                )
            else:
                rec.added_value_in_currency = 0

    @api.depends('current_quantity_svl', 'added_value_in_currency', 'company_id')
    def _compute_new_value_in_currency(self):
        for reval in self:
            product_id = reval.product_id.with_company(reval.company_id)
            reval.new_value_in_currency = product_id.standard_price_in_currency + reval.added_value_in_currency
            if not float_is_zero(reval.current_quantity_svl, precision_rounding=self.product_id.uom_id.rounding):
                reval.new_value_in_currency_by_qty = reval.new_value_in_currency / reval.current_quantity_svl
            else:
                reval.new_value_in_currency_by_qty = 0.0

    def action_validate_revaluation(self):
        product_id = self.product_id.with_company(self.company_id)
        if product_id.categ_id.property_cost_method in ('average', 'fifo') and product_id.categ_id.valuation_currency_id:
            # Update the stardard price in currency in case of AVCO
            # Para actualizar el costo en currency vuelvo a calcular el valor en moneda
            # Si bien hago dos veces el calculo (en el layer y aqui) esto es mas
            # sencillo que obtener el ultimo layer y agregar el valor.

            product_id.with_context(disable_auto_svl=True).standard_price_in_currency += self.added_value_in_currency / self.current_quantity_svl
            res = super(StockValuationLayerRevaluation, self.with_context(
                revaluation_force_currency=product_id.categ_id.valuation_currency_id,
                revaluation_value_in_currency=self.added_value_in_currency,
                )).action_validate_revaluation()
            return res
        return super().action_validate_revaluation()
