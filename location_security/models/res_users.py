##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    restrict_locations = fields.Boolean(
        help="Only allow this user to validate transfers whose source and destination locations are among "
        "the allowed locations or their sublocations.",
    )

    stock_location_ids = fields.Many2many(
        "stock.location",
        "location_security_stock_location_users",
        "user_id",
        "location_id",
        "Allowed Locations",
        help="Locations, and their sublocations, this user can validate transfers from and to. Include the "
        "partner locations the transfers use too, such as Vendors or Customers.",
    )

    def _get_allowed_stock_locations(self):
        self.ensure_one()
        return self.env["stock.location"].search([("id", "child_of", self.stock_location_ids.ids)])
