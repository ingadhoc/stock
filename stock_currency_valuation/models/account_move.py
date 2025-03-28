from collections import defaultdict

from odoo import models, api, fields
from odoo.tools.float_utils import float_compare, float_is_zero


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        income_currency_exchange_account_id = self.company_id.income_currency_exchange_account_id.id
        return super(AccountMove, self.with_context(
            bypass_update_product_price=True,
            force_input_acount=income_currency_exchange_account_id,
            default_bypass_currency_valuation=True)
        )._post(soft=soft)

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get('revaluation_force_currency'):
            vals_list = self.alter_vals_for_revaluation_in_currency(vals_list)
        res_ids = super(AccountMove, self).create(vals_list)
        return res_ids

    def alter_vals_for_revaluation_in_currency(self, vals_list):
        valuation_currency_id = self.env.context.get('revaluation_force_currency').id
        value_in_currency = self.env.context.get('revaluation_value_in_currency')
        vals_list[0]['line_ids'][0][2].update(({
                    'currency_id': valuation_currency_id,
                    'amount_currency': abs(value_in_currency)
        }))
        vals_list[0]['line_ids'][1][2].update(({
                    'currency_id': valuation_currency_id,
                    'amount_currency': abs(value_in_currency) * -1
        }))
        return vals_list
