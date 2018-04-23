##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models
# from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = "stock.move"

    procurement_request_id = fields.Many2one(
        related='procurement_id.procurement_request_id',
        readonly=True,
    )
