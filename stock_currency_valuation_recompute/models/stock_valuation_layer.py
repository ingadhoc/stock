from odoo import fields, models


class StockValuationLayer(models.Model):
    _inherit = "stock.valuation.layer"

    pdiff_quantity = fields.Float(
        digits="Product Unit of Measure",
        readonly=True,
        copy=False,
        help="Quantity on hand a vendor bill price difference corrected.",
    )
