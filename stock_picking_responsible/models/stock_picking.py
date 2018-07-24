##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    user_id = fields.Many2one(
        'res.users',
        string="Responsible"
    )
