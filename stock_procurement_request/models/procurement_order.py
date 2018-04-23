##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models
# from odoo.exceptions import UserError


class ProcurementOrder(models.Model):
    _inherit = "procurement.order"

    procurement_request_id = fields.Many2one(
        'stock.procurement.request',
        'Procurement Request',
    )
