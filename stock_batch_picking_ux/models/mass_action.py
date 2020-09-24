# Copyright 2014 Camptocamp SA - Guewen Baconnier
# Copyright 2018 Tecnativa - Vicent Cubells
# Copyright 2019 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api
from odoo.models import TransientModel


class StockPickingMassAction(TransientModel):
    _inherit = 'stock.picking.mass.action'

    @api.multi
    def mass_action(self):
        self.ensure_one()

        # Get draft pickings and confirm them if asked
        if self.confirm:
            draft_picking_lst = self.picking_ids.\
                filtered(lambda x: x.state == 'draft').\
                sorted(key=lambda r: r.scheduled_date)
            draft_picking_lst.action_confirm()

        # check availability if asked
        if self.check_availability:
            pickings_to_check = self.picking_ids.\
                filtered(lambda x: x.state not in [
                    'draft',
                    'cancel',
                    'done',
                ]).\
                sorted(key=lambda r: r.scheduled_date)
            pickings_to_check.action_assign()

        # Get all pickings ready to transfer and transfer them if asked
        if self.transfer:
            # FIX
            # fix porque si el picking esta parcialmente disponible
            assigned_picking_lst = self.picking_ids.\
                filtered(lambda x: x.state in ['assigned', 'partially_available']).\
                sorted(key=lambda r: r.scheduled_date)
            # End fix
            quantities_done = sum(
                move_line.qty_done for move_line in
                assigned_picking_lst.mapped('move_line_ids').filtered(
                    lambda m: m.state not in ('done', 'cancel')))
            if not quantities_done:
                return assigned_picking_lst.action_immediate_transfer_wizard()
            if any([pick._check_backorder() for pick in assigned_picking_lst]):
                return assigned_picking_lst.action_generate_backorder_wizard()
            assigned_picking_lst.action_done()
