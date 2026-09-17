from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("stock_ux_quant_import")
class TestQuantImportMessages(TransactionCase):
    """An import must say which row is wrong and why, must not refuse a key column that
    only repeats what the stock line already holds, and must not take a column that moves
    stock behind the back of the adjustment."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids += cls.env.ref("stock.group_stock_manager")
        cls.env.user.group_ids += cls.env.ref("stock_ux.group_stock_inventory_adjustment")
        cls.location = cls.env.ref("stock.stock_location_stock")
        cls.product = cls.env["product.product"].create(
            {
                "name": "Counted Product",
                "is_storable": True,
            }
        )
        cls.env["stock.quant"]._update_available_quantity(cls.product, cls.location, 10)
        cls.quant = cls.env["stock.quant"].search(
            [
                ("product_id", "=", cls.product.id),
                ("location_id", "=", cls.location.id),
            ]
        )

    def _load(self, fields, rows):
        return self.env["stock.quant"].with_context(import_file=True).load(fields, rows)

    def _errors(self, result):
        return [message for message in result["messages"] if message["type"] == "error"]

    def test_export_and_reimport_keeps_the_key_columns(self):
        """The file everybody builds is an export: it carries the key columns untouched."""
        fields = ["id", "product_id", "location_id", "inventory_quantity"]
        rows = self.quant.export_data(fields)["datas"]
        rows[0][3] = "4"

        result = self._load(fields, rows)

        self.assertFalse(self._errors(result), self._errors(result))
        self.quant.action_apply_inventory()
        self.assertEqual(self.quant.quantity, 4)

    def test_moving_a_line_to_another_product_still_refused(self):
        other = self.env["product.product"].create({"name": "Other Product", "is_storable": True})
        with self.assertRaises(UserError) as error:
            self.quant.with_context(inventory_mode=True).write({"product_id": other.id})
        self.assertIn(other.name, str(error.exception), "the message must name the conflict")

    def test_untracked_product_is_reported_row_by_row(self):
        untracked = [
            self.env["product.product"].create({"name": name, "is_storable": False})
            for name in ("Untracked One", "Untracked Two")
        ]

        result = self._load(
            ["product_id", "location_id", "inventory_quantity"],
            [[product.name, self.location.complete_name, "5"] for product in untracked],
        )

        errors = self._errors(result)
        self.assertEqual(len(errors), 2, "each row gets its own message, not one for all")
        for error, product in zip(errors, untracked):
            self.assertIn(product.name, error["message"])
            self.assertEqual(error["rows"]["from"], error["rows"]["to"], "the message must point at one row")

    def test_column_that_cannot_be_imported_is_named(self):
        result = self._load(
            ["product_id", "location_id", "quantity", "inventory_quantity"],
            [[self.product.name, self.location.complete_name, "10", "4"]],
        )

        errors = self._errors(result)
        self.assertTrue(errors)
        self.assertIn("Quantity", errors[0]["message"])

    def test_on_hand_quantity_is_never_written_straight(self):
        """Writing it would move stock with no move behind it, and core takes it silently
        on the update path."""
        rows = self.quant.export_data(["id"])["datas"]
        rows[0].append("99")

        result = self._load(["id", "quantity"], rows)

        self.assertTrue(self._errors(result))
        self.assertEqual(self.quant.quantity, 10, "the file cannot set the stock on hand")

    def test_file_that_does_not_say_where_the_count_was_taken(self):
        """With a virtual warehouse in the middle, guessing lands the count on stock that
        looks real."""
        fields = ["product_id", "inventory_quantity"]
        rows = [[self.product.name, "4"]]
        self.assertFalse(self._errors(self._load(fields, rows)), "one warehouse, nothing to guess")

        self.env["stock.warehouse"].create({"name": "Second Warehouse", "code": "SWH"})
        errors = self._errors(self._load(fields, rows))

        self.assertTrue(errors)
        self.assertIn(self.location.display_name, errors[0]["message"])
