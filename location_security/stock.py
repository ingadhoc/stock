# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from openerp import models, api, fields, _
from openerp.exceptions import Warning


class stock_location(models.Model):
    _inherit = 'stock.location'

    user_ids = fields.Many2many(
        'res.users',
        'location_security_stock_location_users',
        'location_id',
        'user_id',
        'Users')

    @api.one
    def do_prepare_partial(self, partial_datas):
        user = self.env['res.users'].browse(self._uid)
        if self.user_has_groups(
                'location_security.restrict_locations'):
            title = _('Invalid Location')
            message = _(
                'You cannot process this move since it is in a location'
                ' you do not control.')
            if not user.can_move_stock_to_location(self.location_id.id):
                raise Warning(title, message)
            if not user.can_move_stock_to_location(
                    self.location_dest_id.id):
                raise Warning(title, message)


class stock_picking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def force_assign(self):
        for pick in self:
            move_ids = [
                x.id for x in pick.move_lines if x.state in ['confirmed', 'waiting']]
            self.env['stock.move'].check_location_security_constrains(move_ids)
        return super(stock_picking, self).force_assign()


class stock_move(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def do_prepare_partial(self, partial_datas):
        self.check_location_security_constrains()
        return super(stock_move, self).do_prepare_partial(partial_datas)

    @api.multi
    def force_assign(self):
        self.check_location_security_constrains()
        return super(stock_move, self).force_assign()

    @api.multi
    def action_done(self):
        self.check_location_security_constrains()
        return super(stock_move, self).action_done()

    @api.one
    def check_location_security_constrains(self):
        user = self.env['res.users'].browse(self._uid)
        if self.user_has_groups(
                'location_security.restrict_locations'):
            title = _('Invalid Location')
            message = _(
                'You cannot process this move since you do not control'
                ' the location "%s".')
            if not user.can_move_stock_to_location(self.location_id.id):
                raise Warning(
                    title, message % self.location_id.name)
            if not user.can_move_stock_to_location(self.location_dest_id.id):
                raise Warning(
                    title, message % self.location_dest_id.name)
