# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    user_picking_id = fields.Many2one(
        'res.users',
        string="User Preparer"
    )


class StockMove(models.Model):
    _inherit = 'stock.move'

    create_user_so_id = fields.Many2one(
        'res.users',
        related='picking_id.sale_id.create_uid',
        string="Usuario Creador de la OE",
        readonly=True,
    )
    create_user_picking_id = fields.Many2one(
        'res.users',
        related='picking_id.user_picking_id',
        string="Usuario Preparador de la OE",
        readonly=True,
    )
