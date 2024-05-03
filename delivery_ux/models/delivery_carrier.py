from odoo import models, fields


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    partner_id = fields.Many2one(
        'res.partner',
        string='Carrier Address',
        help="Utilizado para el remito."
    )
