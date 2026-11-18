from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools.safe_eval import safe_eval


@tagged("post_install", "-at_install")
class TestProductIsStorableDefault(TransactionCase):
    """Inventory > Products defaults is_storable to True: only goods may keep it."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        action = cls.env.ref("stock.product_template_action_product")
        cls.action_context = safe_eval(action.context)
        cls.Template = cls.env["product.template"].with_context(**cls.action_context)

    def test_action_still_defaults_is_storable(self):
        # if Odoo drops this default, the override in stock_ux is no longer needed
        self.assertTrue(self.action_context.get("default_is_storable"))

    def test_create_from_inventory_action(self):
        goods, service = self.Template.create(
            [
                {"name": "Goods", "type": "consu"},
                {"name": "Service", "type": "service"},
            ]
        )
        self.assertTrue(goods.is_storable)
        self.assertFalse(service.is_storable)

    def test_import_from_inventory_action(self):
        result = self.Template.load(
            ["name", "type"],
            [["Imported goods", "consu"], ["Imported service", "service"]],
        )
        self.assertFalse(result["messages"])
        goods, service = self.env["product.template"].browse(result["ids"])
        self.assertTrue(goods.is_storable)
        self.assertFalse(service.is_storable)

    def test_service_variant_from_inventory_action(self):
        product = (
            self.env["product.product"]
            .with_context(**self.action_context)
            .create({"name": "Service variant", "type": "service"})
        )
        self.assertFalse(product.is_storable)
