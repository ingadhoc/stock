from odoo import models, fields, api


class productTemplate(models.Model):

    _inherit = 'product.template'

    valuation_currency_id = fields.Many2one(
        related="categ_id.valuation_currency_id",
        currency_field='valuation_currency_id'
    )
    standard_price_in_currency = fields.Float(
        'Cost', compute='_compute_standard_price_in_currency',
        inverse='_set_standard_price_in_currency', search='_search_standard_price_in_currency',
        digits='Product Price', groups="base.group_user",
    )
    replenishment_cost_type = fields.Selection(
        selection_add=[('average_in_currency', 'Average Cost in Currency')],
        ondelete={'average_in_currency': 'set default'}
    )

    @api.depends()
    def _compute_replenishment_cost(self):
        use_average_in_currency = self.filtered(lambda x: x.replenishment_cost_type == "average_in_currency")
        super(productTemplate, self - use_average_in_currency)._compute_replenishment_cost()
        if use_average_in_currency:
            company_id = self.env.company
            # domain = [
            #     ('product_tmpl_id', 'in', use_average_in_currency.ids),
            #     ('company_id', '=', company_id.id),
            # ]
            # groups = self.env['stock.valuation.layer']._read_group(domain, ['value_in_currency:sum', 'quantity:sum'],
            #                                                        ['product_tmpl_id'])
            # products_avg_cost = {group['product_tmpl_id'][0]: group['value_in_currency'] / group['quantity']
            #                      if group['quantity'] else 0 for group in groups}
            for rec in use_average_in_currency:
                product_currency = rec.currency_id
                #product_cost = products_avg_cost.get(rec.id) or 0
                price_unit = rec.valuation_currency_id._convert(
                            from_amount=rec.standard_price_in_currency,
                            to_currency=product_currency,
                            company=company_id,
                            date=fields.date.today(),
                        )
                rec.update({
                    'replenishment_base_cost_currency_id': rec.valuation_currency_id.id,
                    'replenishment_base_cost_on_currency': price_unit,
                    'replenishment_cost': price_unit,
                    'replenishment_base_cost': rec.standard_price_in_currency,
                })

    @api.depends_context('company')
    @api.depends('product_variant_ids', 'product_variant_ids.standard_price')
    def _compute_standard_price_in_currency(self):
        # Depends on force_company context because standard_price_in_currency is company_dependent
        # on the product_product
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.standard_price_in_currency = template.product_variant_ids.standard_price_in_currency
        for template in (self - unique_variants):
            template.standard_price_in_currency = 0.0

    def _set_standard_price_in_currency(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.standard_price_in_currency = template.standard_price_in_currency

    def _search_standard_price_in_currency(self, operator, value):
        products = self.env['product.product'].search([('standard_price_in_currency', operator, value)], limit=None)
        return [('id', 'in', products.mapped('product_tmpl_id').ids)]
