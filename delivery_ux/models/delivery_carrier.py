from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import ValidationError


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    partner_id = fields.Many2one(
        'res.partner',
        string='Carrier Address',
        help="Utilizado para el remito."
    )
    zip_codes = fields.Char(
        string="Zip codes",
        help="A list of zip codes availables for this shipping method.\n"
             "If the zip code of the client is not in this list it will not be able to select it."
    )

    @api.constrains('zip_codes')
    def check_zip_codes_list(self):
        try:
            if self.zip_codes and not isinstance(safe_eval(self.zip_codes), list):
                raise Exception
        except Exception:
            raise ValidationError(_("Invalid expression, the zip codes must be a list of numbers, something like: ['code1', 'code2']"))

    def _match_address(self, partner):
        res = super()._match_address(partner)
        if res and self.zip_codes and partner.zip not in safe_eval(self.zip_codes):
            return False
        return res
