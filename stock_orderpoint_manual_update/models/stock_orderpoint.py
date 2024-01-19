from odoo import models, fields


class StockWarehouseOrderpoint(models.Model):
    """ Defines Minimum stock rules. """
    _inherit = "stock.warehouse.orderpoint"

    qty_forecast_stored = fields.Float(
        string="Previsión",
    )

    def _get_orderpoint_action(self):
        action = super()._get_orderpoint_action()
        self.update_qty_forecast()
        return action

    def update_qty_forecast(self):
        orderpoints = self.with_context(active_test=False).search([])
        for rec in orderpoints:
            rec.qty_forecast_stored = rec.qty_forecast
