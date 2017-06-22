# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models
# from openerp.exceptions import UserError


class StockMove(models.Model):
    _inherit = "stock.move"

    procurement_request_id = fields.Many2one(
        related='procurement_id.procurement_request_id',
    )
