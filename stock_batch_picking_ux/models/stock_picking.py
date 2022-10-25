# @2016 Cyril Gaudin, Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.tools import float_is_zero


class StockPicking(models.Model):
    _inherit = "stock.picking"

    # sobreescribimos esta funcion por el FIX, deberia ir a la oca una vez
    # depurado
    def force_transfer(self, force_qty=True):
        """ Do the picking transfer (by calling do_transfer)

        If *force_qty* is True, force the transfer for all product_qty
        when qty_done is 0.

        Otherwise, process only pack operation with qty_done.
        If a picking has no qty_done filled, we released it from his batch
        """
        for pick in self:
            if pick.state != 'assigned':
                pick.action_assign()
                # FIX
                # fix porque si el picking esta parcialmente disponible
                # no lo termina procesando
                # if pick.state != 'assigned':
                if pick.state not in ['assigned', 'partially_available']:
                    continue
                # END FIX

            if force_qty:
                for pack in pick.move_line_ids:
                    pack.qty_done = pack.product_uom_qty
            else:
                if all(
                        float_is_zero(
                            pack.qty_done,
                            precision_rounding=pack.product_uom_id.rounding)
                        for pack in pick.move_line_ids):
                    # No qties to process, release out of the batch
                    pick.batch_id = False
                    continue
                else:
                    for pack in pick.move_line_ids:
                        if not pack.qty_done:
                            pack.unlink()

            pick._action_done()

    def _action_generate_backorder_wizard(self, show_transfers=False):
        if self._context.get('picking_batches', False):
            wiz = self.env['stock.backorder.confirmation'].create({'pick_ids': [(4, p.id) for p in self]})
            wiz.process()
            self._context.get('picking_batches').write({'state': 'done'})
            return True
        else:
            return super(StockPicking, self)._action_generate_backorder_wizard(show_transfers=show_transfers)
