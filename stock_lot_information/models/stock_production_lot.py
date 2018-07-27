from odoo import models, fields


class StockProductionLot(models.Model):

    _inherit = 'stock.production.lot'

    ref_initial = fields.Integer(
        string='Initial reference'
    )
    ref_final = fields.Integer(
        string='Final reference'
    )
