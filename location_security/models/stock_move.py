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
        moves = self.filtered(lambda x: x.state in ['done', 'cancel'])
        if not moves or not self.env.user.restrict_locations:
            return True
        user_locations = self.env.user.stock_location_ids
        for user_location in user_locations:
            location = user_locations.search(
                [('id', 'child_of', user_location.id)])
            user_locations |= location
        message = _(
            'Invalid Location. You cannot process this move since you do '
            'not control the location "%s".')
        for rec in moves:
            if rec.location_id not in user_locations:
                raise ValidationError(message % rec.location_id.name)
            elif rec.location_dest_id not in user_locations:
                raise ValidationError(message % rec.location_dest_id.name)
