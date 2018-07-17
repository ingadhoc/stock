from odoo import models, fields


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    partner_id = fields.Many2one(
        'res.partner',
        string='Transporter Company',
        required=True,
        help="The partner that is doing the delivery service."
    )
