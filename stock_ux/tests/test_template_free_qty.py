from odoo.fields import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestTemplateFreeQty(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        location = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1).lot_stock_id
        attribute = cls.env["product.attribute"].create(
            {
                "name": "Free Qty Attribute",
                "value_ids": [Command.create({"name": "A"}), Command.create({"name": "B"})],
            }
        )
        Template = cls.env["product.template"]
        vals = {"type": "consu", "is_storable": True}
        attribute_line = [
            Command.create({"attribute_id": attribute.id, "value_ids": [Command.set(attribute.value_ids.ids)]})
        ]
        cls.with_variants = Template.create({**vals, "name": "Free Qty Variants", "attribute_line_ids": attribute_line})
        cls.mixed = Template.create({**vals, "name": "Free Qty Mixed", "attribute_line_ids": attribute_line})
        cls.single = Template.create({**vals, "name": "Free Qty Single"})
        cls.empty = Template.create({**vals, "name": "Free Qty Empty"})
        variant_a, variant_b = cls.with_variants.product_variant_ids
        Quant = cls.env["stock.quant"]
        Quant._update_available_quantity(variant_a, location, 26.0)
        Quant._update_available_quantity(variant_b, location, 30.0)
        Quant._update_available_quantity(cls.mixed.product_variant_ids[0], location, 10.0)
        Quant._update_available_quantity(cls.single.product_variant_id, location, 15.0)
        cls.templates = cls.with_variants | cls.mixed | cls.single | cls.empty

    def _search(self, operator, value):
        return self.env["product.template"].search([("id", "in", self.templates.ids), ("free_qty", operator, value)])

    def test_search_template_by_free_qty(self):
        self.assertEqual(self._search(">", 0), self.with_variants | self.mixed | self.single)
        self.assertEqual(self._search(">=", 20), self.with_variants)
        # A template matches when any of its variants does, as qty_available
        self.assertEqual(self._search("=", 0), self.mixed | self.empty)
        self.assertEqual(self._search("!=", 0), self.with_variants | self.mixed | self.single)
