##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    analytic_tag_ids = fields.Many2many(
        'account.analytic.tag',
        states={'done': [('readonly', True)]},
    )

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        states={'done': [('readonly', True)]},
    )

    def _prepare_account_move_line(
            self, qty, cost, credit_account_id, debit_account_id, description):
        result = super()._prepare_account_move_line(
            qty=qty, cost=cost, credit_account_id=credit_account_id,
            debit_account_id=debit_account_id, description=description)
        for res in result:
            if (
                res[2]["account_id"]
                != self.product_id.categ_id.property_stock_valuation_account_id.id
            ):
                # Add analytic account in debit line
                if self.analytic_account_id:
                    res[2].update({"analytic_account_id": self.analytic_account_id.id})
                if self.analytic_tag_ids:
                    res[2]['analytic_tag_ids'] = [(6, 0, self.analytic_tag_ids.ids)]
        return result
