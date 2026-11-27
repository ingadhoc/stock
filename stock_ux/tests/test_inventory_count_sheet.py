from lxml import html
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestInventoryCountSheet(TransactionCase):
    """The count sheet prints available and on hand apart only when the expected quantity may be shown."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.location = cls.env.ref("stock.stock_location_stock")
        cls.product = cls.env["product.product"].create({"name": "Counted Lamp", "is_storable": True})
        cls.env["stock.quant"]._update_available_quantity(cls.product, cls.location, 10)
        # Reserve 4 of the 10 so available and on hand differ, without depending on how pickings reserve.
        cls.env["stock.quant"]._update_reserved_quantity(cls.product, cls.location, 4)
        cls.quant = cls.env["stock.quant"].search(
            [("product_id", "=", cls.product.id), ("location_id", "=", cls.location.id)]
        )

    def _render(self, show_expected):
        self.env["ir.config_parameter"].sudo().set_param(
            "stock.show_expected_quantity_count", "True" if show_expected else "False"
        )
        content, _ = self.env["ir.actions.report"]._render_qweb_html("stock.action_report_inventory", self.quant.ids)
        return html.fromstring(content)

    def _cell(self, doc, css_class):
        cells = doc.xpath(f"//td[contains(concat(' ', normalize-space(@class), ' '), ' {css_class} ')]")
        self.assertEqual(len(cells), 1)
        return " ".join(cells[0].text_content().split())

    def test_expected_shown_prints_available_on_hand_and_counted(self):
        self.quant.with_context(inventory_mode=True).inventory_quantity = 9
        doc = self._render(show_expected=True)
        headers = [" ".join(th.text_content().split()) for th in doc.xpath("//thead//th")]
        self.assertIn("Available Quantity", headers)
        self.assertIn("On Hand Quantity", headers)
        self.assertIn("Counted Quantity", headers)
        self.assertRegex(self._cell(doc, "o_td_available_quantity"), r"^6\.00")
        self.assertRegex(self._cell(doc, "o_td_quantity"), r"^10\.00")
        self.assertRegex(self._cell(doc, "o_td_counted_quantity"), r"^9\.00")

    def test_expected_shown_leaves_counted_blank_until_counted(self):
        doc = self._render(show_expected=True)
        self.assertEqual(self._cell(doc, "o_td_counted_quantity"), "")

    def test_blind_sheet_unchanged(self):
        doc = self._render(show_expected=False)
        headers = [" ".join(th.text_content().split()) for th in doc.xpath("//thead//th")]
        self.assertNotIn("Available Quantity", headers)
        self.assertNotIn("Counted Quantity", headers)
        self.assertIn("Quantity", headers)
        self.assertFalse(doc.xpath("//td[contains(@class, 'o_td_available_quantity')]"))
        self.assertFalse(doc.xpath("//td[contains(@class, 'o_td_counted_quantity')]"))

    def test_physical_inventory_offers_available_column(self):
        arch = self.env["stock.quant"].get_view(
            self.env.ref("stock.view_stock_quant_tree_inventory_editable").id, "list"
        )["arch"]
        node = html.fromstring(arch).xpath("//field[@name='available_quantity']")
        self.assertTrue(node)
        self.assertEqual(node[0].get("optional"), "hide")
