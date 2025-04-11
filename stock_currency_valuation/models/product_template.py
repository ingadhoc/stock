from odoo import api, fields, models


class productTemplate(models.Model):
    _inherit = "product.template"

    valuation_currency_id = fields.Many2one(
        related="categ_id.valuation_currency_id",
    )
    standard_price_in_currency = fields.Float(
        "Cost",
        compute="_compute_standard_price_in_currency",
        inverse="_inverse_standard_price_in_currency",
        search="_search_standard_price_in_currency",
        digits="Product Price",
        groups="base.group_user",
    )
    replenishment_cost_type = fields.Selection(
        selection_add=[("average_in_currency", "Average Cost in Currency")],
        ondelete={"average_in_currency": "set default"},
    )

    @api.depends("standard_price_in_currency")
    def _compute_replenishment_cost(self):
        use_average_in_currency = self.filtered(lambda x: x.replenishment_cost_type == "average_in_currency")
        super(productTemplate, self - use_average_in_currency)._compute_replenishment_cost()
        company_id = self.env.company
        for rec in use_average_in_currency:
            product_currency = rec.currency_id
            replenishment_cost_rule = rec.replenishment_cost_rule_id
            replenishment_cost = rec.standard_price_in_currency
            if replenishment_cost_rule:
                replenishment_cost = replenishment_cost_rule.compute_rule(replenishment_cost, rec)
            replenishment_base_cost_on_currency = rec.valuation_currency_id._convert(
                from_amount=replenishment_cost,
                to_currency=product_currency,
                company=company_id,
                date=fields.date.today(),
            )
            rec.update(
                {
                    "replenishment_base_cost_on_currency": replenishment_base_cost_on_currency,
                    "replenishment_cost": replenishment_cost,
                }
            )

    @api.depends_context("company")
    @api.depends("product_variant_ids", "product_variant_ids.standard_price")
    def _compute_standard_price_in_currency(self):
        # Por ahora hacemos esto porque replishment cost no es compatible al 100% con variantes
        # obtenemos el precio del primer producto
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.standard_price_in_currency = template.product_variant_ids.standard_price_in_currency
        for template in self - unique_variants:
            template.standard_price_in_currency = template.product_variant_ids[:1].standard_price_in_currency

    def _inverse_standard_price_in_currency(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.standard_price_in_currency = template.standard_price_in_currency

    def _search_standard_price_in_currency(self, operator, value):
        products = self.env["product.product"].search([("standard_price_in_currency", operator, value)], limit=None)
        return [("id", "in", products.mapped("product_tmpl_id").ids)]
