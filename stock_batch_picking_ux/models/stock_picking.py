# @2016 Cyril Gaudin, Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


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
                if all(pack.qty_done == 0 for pack in pick.move_line_ids):
                    # No qties to process, release out of the batch
                    pick.batch_picking_id = False
                    continue
                else:
                    for pack in pick.move_line_ids:
                        if not pack.qty_done:
                            pack.unlink()
                        else:
                            pack.product_uom_qty = pack.qty_done

            pick.do_transfer()
