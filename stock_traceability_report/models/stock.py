# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.production.lot'

    @api.one
    def _get_moves(self):
        self.move_ids = self.quant_ids.mapped('history_ids')

    move_ids = fields.One2many('stock.move', compute='_get_moves')
