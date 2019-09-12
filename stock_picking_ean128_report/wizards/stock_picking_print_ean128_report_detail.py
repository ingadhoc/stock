##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class StockPickingEan128ReportDetail(models.TransientModel):
    """ We create a readonly related field for each one because if not odoo
    view doesn't save the values
    """
    _name = 'stock.picking.print_ean128_report_detail'
    _description = 'Stock Picking Print EAN128 Report Detail'

    stock_picking_report_id = fields.Many2one(
        'stock.picking.print_ean128_report',
        'Picking Report EAN Print',
    )
    quantity = fields.Integer()
    move_line_id = fields.Many2one(
        'stock.move.line',
    )
    product_id = fields.Many2one(
        'product.product',
        string="Product",
        readonly=True,
    )
    lot_id = fields.Many2one(
        'stock.production.lot',
        string='Lot',
        readonly=True,
    )
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='UOM',
        readonly=True,
    )
