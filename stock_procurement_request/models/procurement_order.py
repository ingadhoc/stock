# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models
# from openerp.exceptions import UserError


class ProcurementOrder(models.Model):
    _inherit = "procurement.order"

    procurement_request_id = fields.Many2one(
        'stock.procurement.request',
        'Procurement Request',
    )
