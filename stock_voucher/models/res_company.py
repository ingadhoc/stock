##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class res_company(models.Model):
    _inherit = 'res.company'

    automatic_declare_value = fields.Boolean(
        'Automatic Declare Value',
        help="The declared value will be on the currency of the company"
    )
    restrict_number_package = fields.Boolean(
        'Restrict number of Package'
    )
