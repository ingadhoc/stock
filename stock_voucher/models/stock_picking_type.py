##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    book_required = fields.Boolean(
        string='Book Required?',
        help='If true, then a book will be requested on transfers of this '
        'type and a will automatically print the stock voucher.',
    )
    voucher_required = fields.Boolean(
        string='Voucher Required?',
        help='If true, voucher numbers will be required before validation',
    )
    # only for incoming
    voucher_number_unique = fields.Boolean(
        string='Book Unique?',
        help='If true, voucher numbers will be required to be unique for same'
        ' partner',
    )
    book_id = fields.Many2one(
        'stock.book',
        'Book',
        help='Book suggested for pickings of this type',
    )
    pricelist_id = fields.Many2one(
        'product.pricelist',
        'Pricelist',
        help='If you choose a pricelist, "Automatic Declare Value" is'
        ' enable on company and not sale order is found linked to the'
        ' picking, we will suggest declared value using this pricelist',
    )
    automatic_declare_value = fields.Boolean(
        help="The declared value will be on the currency of the company",
    )
    restrict_number_package = fields.Boolean(
    )
