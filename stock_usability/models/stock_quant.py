# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api


class StockQuant(models.Model):
    _inherit = "stock.quant"

    @api.model
    def _prepare_account_move_line(
            self, move, qty, cost, credit_account_id, debit_account_id):
        if move.product_id.currency_id != move.company_id.currency_id:
            if move.product_id.cost_method == 'average':
                valuation_amount = cost if move.location_id.usage != 'internal'\
                    and move.location_dest_id.usage == 'internal'\
                    else move.product_id.standard_price
            else:
                valuation_amount = cost if move.product_id.cost_method == 'real'\
                    else move.product_id.standard_price
            self = self.with_context(force_valuation_amount=move.product_id.
                currency_id.compute(
                    valuation_amount, move.company_id.currency_id, round=True))
        return super(
            StockQuant, self)._prepare_account_move_line(
            move=move, qty=qty, cost=cost, credit_account_id=credit_account_id,
            debit_account_id=debit_account_id)
