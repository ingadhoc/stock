# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models


class res_company(models.Model):
    _inherit = 'res.company'

    automatic_declare_value = fields.Boolean(
        'Automatic Declare Value'
    )
    restrict_number_package = fields.Boolean(
        'Restrict number of Package'
    )
