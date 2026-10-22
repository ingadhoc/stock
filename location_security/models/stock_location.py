##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class StockLocation(models.Model):
    _inherit = "stock.location"

    restricted_user_ids = fields.Many2many(
        "res.users",
        string="Restricted Users",
        compute="_compute_restricted_user_ids",
        help="Users with restricted locations allowed on this location. Users without the restriction can operate "
        "every location; users allowed on a parent location can operate this one too.",
    )

    def _compute_restricted_user_ids(self):
        # Calculado y sin inverso: las ubicaciones permitidas se cambian solo
        # desde el usuario, que pide permisos de administración de usuarios.
        users = self.env["res.users"].search(
            [("restrict_locations", "=", True), ("stock_location_ids", "in", self.ids)]
        )
        for rec in self:
            rec.restricted_user_ids = users.filtered(lambda u: rec in u.stock_location_ids)
