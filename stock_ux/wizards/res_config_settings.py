##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_operation_used_lots = fields.Boolean(
        'Show Used Lots on Picking Operations',
        implied_group='stock_ux.group_operation_used_lots',
    )

    delivery_slip_use_origin = fields.Boolean(
        'En Comprobantes de Transferencia usar Descripción de Origen',
        config_parameter='stock_ux.delivery_slip_use_origin'
    )
