from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestRevaluationInCurrency(TransactionCase):
    def test_revaluation_updates_standard_price_in_currency(self):
        """La revaluacion tiene que impactar el costo en moneda secundaria de la ficha."""
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
        product.standard_price = 1000.0
        product.standard_price_in_currency = 1.0

        # ingreso 2 unidades por ajuste de inventario para tener layers con remaining_qty
        warehouse = self.env["stock.warehouse"].search([("company_id", "=", company.id)], limit=1)
        self.env["stock.quant"].with_context(inventory_mode=True).create(
            {
                "product_id": product.id,
                "location_id": warehouse.lot_stock_id.id,
                "inventory_quantity": 2.0,
            }
        ).action_apply_inventory()

        wizard = (
            self.env["stock.valuation.layer.revaluation"]
            .with_company(company)
            .create({"product_id": product.id, "added_value": 2000.0, "reason": "test"})
        )
        expected = 1.0 + wizard.added_value_in_currency / 2.0
        # el preview del wizard tiene que anticipar el costo que va a quedar en la ficha
        self.assertAlmostEqual(wizard.new_value_in_currency, expected * 2.0, places=2)
        self.assertAlmostEqual(wizard.new_value_in_currency_by_qty, expected, places=2)

        wizard.action_validate_revaluation()

        self.assertAlmostEqual(product.standard_price, 2000.0, places=2)
        self.assertAlmostEqual(product.standard_price_in_currency, expected, places=2)
        # esta lectura ademas cachea el valor del template para el chequeo de abajo
        self.assertAlmostEqual(product.product_tmpl_id.standard_price_in_currency, expected, places=2)

        # si solo se mueve el costo en moneda (ej. un landed cost), el template tiene que seguirlo
        product.standard_price_in_currency = 5.0
        self.assertAlmostEqual(product.product_tmpl_id.standard_price_in_currency, 5.0, places=2)
