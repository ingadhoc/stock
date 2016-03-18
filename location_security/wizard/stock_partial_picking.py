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
        user = self.env['res.users'].browse(self._uid)
        if self.user_has_groups('location_security.restrict_locations'):
            for partial in self:
                for wizard_line in partial.item_ids:
                    title = _('Invalid Location')
                    message = _('You cannot process this move since it is'
                                ' in a location you do not control.')
                    if not user.can_move_stock_to_location(
                            wizard_line.sourceloc_id.id):
                        raise Warning(title, message)
                    if not user.can_move_stock_to_location(
                            wizard_line.destinationloc_id.id):
                        raise Warning(title, message)
        return super(stock_transfer_details, self).do_detailed_transfer()
