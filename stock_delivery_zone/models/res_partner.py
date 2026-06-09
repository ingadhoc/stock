##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    delivery_zone_id = fields.Many2one(
        comodel_name="stock.delivery.zone",
        string="Zone",
        ondelete="set null",
    )
