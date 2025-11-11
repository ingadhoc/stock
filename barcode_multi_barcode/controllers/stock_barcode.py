from odoo import http
from odoo.addons.stock_barcode.controllers.stock_barcode import StockBarcodeController
from odoo.http import request


class StockBarcodeControllerInherit(StockBarcodeController):
    @http.route("/stock_barcode/get_specific_barcode_data", type="json", auth="user")
    def get_specific_barcode_data(self, **kwargs):
        res = super().get_specific_barcode_data(**kwargs)
        if "product.product" in res:
            barcode = kwargs.get("barcodes_by_model", {}).get("product.product")
            for product in res["product.product"]:
                if product["barcode_ids"]:
                    product["barcode"] = (
                        request.env["product.barcode"]
                        .browse(product["barcode_ids"])
                        .filtered(lambda x: x.name in barcode)
                        .name
                    )
        return res
