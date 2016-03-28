# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from openerp import api, models, _
from openerp.exceptions import Warning


class stock_transfer_details(models.TransientModel):
    _inherit = 'stock.transfer_details'

    @api.multi
    def do_detailed_transfer(self):
        self.ensure_one()
        user = self.env.user
        if user.restrict_locations:
            for wizard_line in self.item_ids:
                message = _('Invalid Location. You cannot process this move '
                            'since it is in a location you do not control.')
                if not user.can_move_stock_to_location(
                        wizard_line.sourceloc_id.id):
                    raise Warning(message)
                if not user.can_move_stock_to_location(
                        wizard_line.destinationloc_id.id):
                    raise Warning(message)
        return super(stock_transfer_details, self).do_detailed_transfer()
