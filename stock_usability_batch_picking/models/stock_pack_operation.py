##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields


class StockPackOperation(models.Model):

    _inherit = 'stock.pack.operation'

    origin = fields.Char(
        related='picking_id.origin',
        readonly=True,
        # we store so we can group
        store=True,
    )
