from odoo import models,api

class StockQuant(models.Model):
    _inherit = 'stock.quant'
    
    @api.onchange('inventory_quantity')
    def _compute_user_id(self):
        for record in self:
            if not record.user_id:
                record.user_id = record.env.user.id

    def _get_inventory_move_values(self, qty, location_id, location_dest_id, out=False):
        res = super(StockQuant, self)._get_inventory_move_values(qty, location_id, location_dest_id, out=out)
        res['move_line_ids'][0][2]['quant_partner_id'] = self.user_id.partner_id.id
        return res
