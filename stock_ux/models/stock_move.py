##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    used_lots = fields.Char(
        compute='_compute_used_lots',
    )
    picking_create_user_id = fields.Many2one(
        'res.users',
        related='picking_id.create_uid',
        string="Picking Creator",
        readonly=True,
    )
    picking_dest_id = fields.Many2one(
        related='move_dest_ids.picking_id',
        readonly=True,
    )
    lots_visible = fields.Boolean(
        related='move_line_ids.lots_visible',
        readonly=True,
    )

    @api.depends(
        'move_line_ids.qty_done',
        'move_line_ids.lot_id',
    )
    def _compute_used_lots(self):
        for rec in self:
            rec.update({'used_lots': ", ".join(rec.move_line_ids.mapped(
                lambda x: "%s (%s)" % (x.lot_id.name, x.qty_done)))})

    @api.multi
    def set_all_done(self):
        for rec in self:
            rec.update({'quantity_done': rec.product_uom_qty})

    @api.model
    def _prepare_account_move_line(
            self, qty, cost, credit_account_id, debit_account_id):
        if self.product_id.currency_id != self.company_id.currency_id:
            self = self.with_context(
                force_valuation_amount=self.product_id.currency_id.compute(
                    cost, self.company_id.currency_id, round=True))
        return super(
            StockMove, self)._prepare_account_move_line(
            qty=qty, cost=cost, credit_account_id=credit_account_id,
            debit_account_id=debit_account_id)
