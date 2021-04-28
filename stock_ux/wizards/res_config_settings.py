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
        'En Comprobantes de Transferencia usar Descripción de Origen'
    )

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res.update(delivery_slip_use_origin=bool(get_param('stock_ux.delivery_slip_use_origin', False)))
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param
        set_param('stock_ux.delivery_slip_use_origin', self.delivery_slip_use_origin)
