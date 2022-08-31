##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api


class StockPicking(models.Model):

    _inherit = 'stock.picking'

    state_detail_id = fields.Many2one(
        'stock.picking.state_detail',
        string='State Detail',
        tracking=True,
        index=True,
        copy=False,
    )

    @api.constrains('state')
    def change_state(self):
        for rec in self:
            domain = [
                ('state', '=', rec.state),
                ('picking_type', '=', rec.picking_type_code)]
            state_detail = self.env['stock.picking.state_detail'].search(domain, order="sequence asc")
            if rec.state_detail_id and rec.state_detail_id in state_detail:
                continue
            rec.state_detail_id = state_detail and state_detail[0]
