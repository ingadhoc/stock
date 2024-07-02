from odoo import api, fields, models


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    removal_priority = fields.Integer(
        related='location_id.removal_priority',
        store=True,
    )
    
    @api.model
    def _get_removal_strategy_domain_order(self, domain, removal_strategy, qty):
        if removal_strategy == 'priority':
            return domain, 'removal_priority ASC, id'
        return super()._get_removal_strategy_domain_order(domain, removal_strategy, qty)

    def _get_removal_strategy_sort_key(self, removal_strategy):
        if removal_strategy == 'priority':
            return lambda q: (q.removal_priority, q.id), False
        return super()._get_removal_strategy_sort_key(removal_strategy)
