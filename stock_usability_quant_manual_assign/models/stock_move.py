# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class StockMove(models.Model):

    _inherit = 'stock.move'

    pack_operation_product_ids = fields.One2many(
        'stock.pack.operation',
        related='picking_id.pack_operation_product_ids',
        readonly=True)
