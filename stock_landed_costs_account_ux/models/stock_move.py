from collections import defaultdict

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _compute_all_account_move_ids(self):
        super()._compute_all_account_move_ids()
        entries_by_move = self._get_landed_cost_entries()
        for move in self:
            landed_cost_entries = entries_by_move.get(move._origin.id)
            if not landed_cost_entries:
                continue
            entries = move.sudo().all_account_move_ids | landed_cost_entries
            move.all_account_move_ids = entries.sorted(lambda entry: (entry.date, entry.id))
            move.account_move_count = len(entries)

    def _get_landed_cost_entries(self):
        """Posted entries of the validated landed costs of these moves, per move.

        Read in ``sudo()``: adjustment lines are readable only by stock managers, and the
        journal entries button shows up in lists any stock user opens.

        Only perpetually valued moves: a landed cost on a receipt that mixes perpetual and
        periodic products books only the perpetual ones, as the stored compute does with
        the invoices.
        """
        move_ids = self._filter_real_time_valuation()._origin.ids
        if not move_ids:
            return {}
        lines = (
            self.env["stock.valuation.adjustment.lines"]
            .sudo()
            .search(
                [
                    ("move_id", "in", move_ids),
                    ("cost_id.state", "=", "done"),
                    ("cost_id.account_move_id.state", "=", "posted"),
                ]
            )
        )
        entries_by_move = defaultdict(lambda: self.env["account.move"].sudo())
        for line in lines:
            entries_by_move[line.move_id.id] |= line.cost_id.account_move_id
        return entries_by_move
