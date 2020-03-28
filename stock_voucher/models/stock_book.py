##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class StockBook(models.Model):
    _name = 'stock.book'
    _description = 'Stock Voucher Book'

    name = fields.Char(
        required=True,
    )
    sequence_id = fields.Many2one(
        'ir.sequence',
        'Stock Voucher Sequence',
        domain=[('code', '=', 'stock.voucher')],
        context="{'default_code': 'stock.voucher', 'default_name': name, "
        "'default_prefix': '000X-', 'default_padding': 8, "
        "'default_implementation': 'no_gap',}",
        required=True,
    )
    lines_per_voucher = fields.Integer(
        required=True,
        help="If voucher don't have a limit, then live 0. If not, this number "
        "will be used to calculate how many sequence are used on each picking",
    )
    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        default=lambda self: self.env.company,
    )
    next_number = fields.Integer(
        related='sequence_id.number_next_actual',
        readonly=False
    )
