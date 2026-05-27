##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    delivery_zone_id = fields.Many2one(
        comodel_name="stock.delivery.zone",
        related="partner_id.delivery_zone_id",
        string="Zone",
        readonly=True,
        ondelete="set null",
    )
