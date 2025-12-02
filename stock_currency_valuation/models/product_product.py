<<<<<<< HEAD
||||||| MERGE BASE
=======
from odoo import models, fields


class productProduct(models.Model):

    _inherit = 'product.product'

    valuation_currency_id = fields.Many2one(related="categ_id.valuation_currency_id",)
    standard_price_in_currency = fields.Float(
        'Cost in currency', company_dependent=True,
        groups="base.group_user",
        readonly=False
    )

    def write(self, vals):
        if 'standard_price' in vals and self.env.context.get('bypass_update_product_price'):
            del vals['standard_price']
        return super().write(vals)

    def _change_standard_price(self, new_price):
        super(productProduct, self.with_context(default_bypass_currency_valuation=True))._change_standard_price(new_price)

>>>>>>> FORWARD PORTED
