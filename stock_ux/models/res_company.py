##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    stock_ux_protect_moves = fields.Boolean(
        string="Protect Stock Moves",
        help="Prevent deletion of stock moves that originate from sales or purchase orders. "
        "Users must make changes from the corresponding order instead.",
        default=True,
    )
