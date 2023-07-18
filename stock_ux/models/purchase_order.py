from odoo import _, api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    def write(self, values):
        self = self.with_context(cancel_from_order=True)
        return super().write(values)

