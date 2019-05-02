from odoo import api, fields, models


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    removal_priority = fields.Integer(
        related='location_id.removal_priority',
        readonly=True,
        store=True,
    )

    @api.model
    def _get_removal_strategy(self, product_id, location_id):
        res = super()._get_removal_strategy(product_id, location_id)
        if product_id.categ_id.removal_by_location_priority:
            res = 'location_priority,%s' % res
        return res

    @api.model
    def _get_removal_strategy_order(self, removal_strategy=None):
        location_priority = False
        if 'location_priority,' in removal_strategy:
            removal_strategy = removal_strategy.replace(
                'location_priority,', '')
            location_priority = True
        res = super()._get_removal_strategy_order(
            removal_strategy=removal_strategy)
        if location_priority:
            res = 'removal_priority ASC, %s' % res
        return res
