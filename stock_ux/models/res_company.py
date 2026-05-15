##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    stock_orderpoint_allow_multiple_over_max = fields.Boolean(
        string="Allow Reordering Rule Multiples Above Max",
        default=True,
        help="If enabled, replenishment rules can round up to the next multiple even when that exceeds the maximum quantity.",
    )
