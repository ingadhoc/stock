# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    user_id = fields.Many2one(
        'res.users',
        string="Responsible"
    )


class StockMove(models.Model):
    _inherit = 'stock.move'

    picking_user_id = fields.Many2one(
        'res.users',
        related='picking_id.user_id',
        string="Picking Responsible",
        readonly=True,
    )
