# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
# from odoo.tools.translate import _


class stock_config_settings(models.TransientModel):
    _inherit = 'stock.config.settings'

    group_operation_used_lots = fields.Boolean(
        'Show Used Lots on Picking Operations',
        implied_group='stock_usability.group_operation_used_lots',
        help="Show selected lots on pack operations"
    )
