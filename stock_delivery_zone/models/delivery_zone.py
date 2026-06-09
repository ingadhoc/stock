##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import fields, models


class StockDeliveryZone(models.Model):
    _name = "stock.delivery.zone"
    _description = "Delivery Zone"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
