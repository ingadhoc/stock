from odoo import api, fields, models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    removal_priority = fields.Integer(
        related="location_id.removal_priority",
        store=True,
    )

    @api.model
    def _get_removal_strategy_order(self, removal_strategy):
        if removal_strategy == "priority":
            return "removal_priority ASC, id"
        return super()._get_removal_strategy_order(removal_strategy)
