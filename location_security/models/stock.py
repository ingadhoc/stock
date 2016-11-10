# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from openerp import models, api, _
from openerp.exceptions import UserError


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.one
    @api.constrains('state', 'location_id', 'location_dest_id')
    def check_user_location_rights(self):
        if self.state == 'draft':
            return True
        user_locations = self.env.user.stock_location_ids
        if self.env.user.restrict_locations:
            message = _(
                'Invalid Location. You cannot process this move since you do '
                'not control the location "%s".')
            if self.location_id not in user_locations:
                raise UserError(message % self.location_id.name)
            elif self.location_dest_id not in user_locations:
                raise UserError(message % self.location_dest_id.name)
