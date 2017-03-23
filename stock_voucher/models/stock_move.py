# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models, api, _
from openerp.exceptions import UserError


class StockMove(models.Model):
    _inherit = "stock.move"

    vouchers = fields.Char(
        related='picking_id.vouchers',
        readonly=True,
        # compute='_compute_vouchers'
    )
    # voucher_ids = fields.One2many(
    #     'stock.picking.voucher',
    #     'picking_id',
    #     'Vouchers',
    #     copy=False
    # )
