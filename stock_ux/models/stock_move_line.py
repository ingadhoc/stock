##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    picking_create_user_id = fields.Many2one(
        'res.users',
        related='move_id.picking_create_user_id',
        string="Picking Creator",
        readonly=True,
    )

    picking_partner_id = fields.Many2one(
        'res.partner',
        'Transfer Destination Address',
        related='move_id.picking_partner_id',
        readonly=True,
    )

    picking_code = fields.Selection(
        related='move_id.picking_code',
        readonly=True,
    )

    @api.multi
    def set_all_done(self):
        for rec in self:
            rec.update({'qty_done': rec.move_id.product_uom_qty})
        if self._context.get('from_popup', False):
            return self[0].move_id.action_show_details()
