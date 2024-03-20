from odoo import models,api

class StockQuant(models.Model):
    _inherit = 'stock.quant'
    
    
    
# Establecemos por defecto al usuario creador
    @api.onchange('inventory_quantity')
    def _onchange_inventory_quantity_user(self):
        if not self.user_id:
            self.user_id = self.env.user
    
    def _get_inventory_move_values(self, qty, location_id, location_dest_id, out=False):
        self.ensure_one()
        move_values = super(StockQuant, self)._get_inventory_move_values(qty, location_id, location_dest_id, out)
        partner_id = self.user_id.partner_id
        move_line_values = {
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom_id.id,
            'qty_done': qty,
            'location_id': location_id.id,
            'location_dest_id': location_dest_id.id,
            'company_id': self.company_id.id or self.env.company.id,
            'lot_id': self.lot_id.id,
            'package_id': out and self.package_id.id or False,
            'result_package_id': (not out) and self.package_id.id or False,
            'owner_id': self.owner_id.id,
            'picking_partner_id': partner_id.id or self.owner_id.id,  # Agregamos el usuario contador
        }
        move_values['move_line_ids'] = [(0, 0, move_line_values)]

        return move_values
