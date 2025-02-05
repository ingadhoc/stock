##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class StockBook(models.Model):
    _inherit = "stock.book"

    autoprinted = fields.Boolean(
        help="If voucher is not an autoprinted, it will assign as many vouchers as pages the report has. "
        "Otherwise, it will assign only one voucher",
    )
