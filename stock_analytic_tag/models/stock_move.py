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

    def _prepare_account_move_line(
            self, qty, cost, credit_account_id, debit_account_id):
        result = super()._prepare_account_move_line(
            qty=qty, cost=cost, credit_account_id=credit_account_id,
            debit_account_id=debit_account_id)
        for res in result:
            res[2]['analytic_tag_ids'] = [(6, 0, self.analytic_tag_ids.ids)]
        return result
