from odoo import models


class Product(models.Model):
    _inherit = "product.product"

    def _get_fields_stock_barcode(self):
        return super()._get_fields_stock_barcode() + [
            "barcode_ids",
        ]
