from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestZeroCostReceipt(TransactionCase):
    def test_zero_cost_purchase_receipt_without_stock(self):
        """Una compra a costo 0 sin stock deja el costo en 0 en las dos monedas, como la capa."""
        company = self.env.company
        categ = self.env["product.category"].create(
            {
                "name": "Categoria valuada en moneda",
                "property_cost_method": "average",
                "property_valuation": "manual_periodic",
                "valuation_currency_id": self.env.ref("base.USD").id,
            }
        )
        product = (
            self.env["product.product"]
            .create({"name": "Producto valuado en moneda", "is_storable": True, "categ_id": categ.id})
            .with_company(company)
        )
        # costo que quedo de movimientos anteriores, ya sin stock
        product.standard_price = 1000.0
        product.standard_price_in_currency = 100.0

        order = self.env["purchase.order"].create(
            {
                "partner_id": self.env["res.partner"].create({"name": "Proveedor"}).id,
                "order_line": [(0, 0, {"product_id": product.id, "product_qty": 1.0, "price_unit": 0.0})],
            }
        )
        order.button_confirm()
        order.picking_ids.button_validate()

        layer = order.picking_ids.move_ids.stock_valuation_layer_ids
        self.assertAlmostEqual(layer.value_in_currency, 0.0, places=2)
        self.assertAlmostEqual(product.standard_price, 0.0, places=2)
        # antes quedaba en 100: la venta siguiente salia a 100 y dejaba saldo con stock 0
        self.assertAlmostEqual(product.standard_price_in_currency, 0.0, places=2)
