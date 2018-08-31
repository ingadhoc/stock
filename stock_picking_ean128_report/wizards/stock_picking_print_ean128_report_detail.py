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

    stock_picking_report_id = fields.Many2one(
        'stock.picking.print_ean128_report',
        'Picking Report EAN Print',
    )
    quantity = fields.Integer()
    product_id_readonly = fields.Many2one(
        related='product_id',
        readonly=True,
    )
    product_id = fields.Many2one(
        'product.product',
        string="Product",
    )
    lot_id_readonly = fields.Many2one(
        readonly=True,
    )
    lot_id = fields.Many2one(
        'stock.production.lot',
        string='Lot',
    )
    product_uom_id_readonly = fields.Many2one(
        related='product_uom_id',
        readonly=True,
    )
    product_uom_id = fields.Many2one(
        'product.uom',
        string='UOM',
    )
