from odoo import fields, models


class StockLot(models.Model):
    _inherit = "stock.lot"

    ref_initial = fields.Integer(string="Initial reference")
    ref_final = fields.Integer(string="Final reference")
