from openerp import models, api


class stock_transfer_details(models.TransientModel):

    _inherit = 'stock.transfer_details'

    @api.multi
    def set_qty(self):
        if self.item_ids:
            for product_line in self.item_ids:
                product_line.quantity = 0
        if self and self[0]:
            return self[0].wizard_view()
