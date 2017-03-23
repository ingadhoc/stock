# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    vouchers = fields.Char(
        related='picking_id.vouchers',
        readonly=True,
    )
