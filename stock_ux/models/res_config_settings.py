##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    stock_orderpoint_allow_multiple_over_max = fields.Boolean(
        string="Allow Reordering Rule Multiples Above Max",
        related="company_id.stock_orderpoint_allow_multiple_over_max",
        readonly=False,
    )

    group_operation_used_lots = fields.Boolean(
        "Show Used Lots on Picking Operations",
        implied_group="stock_ux.group_operation_used_lots",
    )

    delivery_slip_use_origin = fields.Boolean(
        "En Comprobantes de Transferencia usar Descripción de Origen",
        config_parameter="stock_ux.delivery_slip_use_origin",
    )

    delivery_slip_remaining_qty = fields.Boolean(
        "En Comprobantes de Transferencia mostrar cantidades pendientes de entrega",
        config_parameter="stock_ux.delivery_slip_remaining_qty",
    )
