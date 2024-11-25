##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'
    _order = "id"
# La unica funcionalidad de este modulo es cambiar el ordenamiento del las vistas embebidas de stock.move
