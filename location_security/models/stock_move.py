##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models, api, _
from odoo.exceptions import ValidationError


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.constrains('state', 'location_id', 'location_dest_id')
    def check_user_location_rights(self):
        if self.env.user.restrict_locations:
            user_locations = self.env.user.stock_location_ids
            message = _(
                'Invalid Location. You cannot process this move since you do '
                'not control the location "%s".')
            for rec in self.filtered(lambda x: x.state != 'draft'):
                if rec.location_id not in user_locations:
                    raise ValidationError(message % rec.location_id.name)
                elif rec.location_dest_id not in user_locations:
                    raise ValidationError(message % rec.location_dest_id.name)
