from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user


@tagged("stock_ux_quant_import")
class TestQuantImport(TransactionCase):
    """An imported count must replace the quantity of the stock line it belongs to."""

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

    def _load(self, fields, rows, user=None):
        quants = self.env["stock.quant"]
        return quants.with_user(user or self.env.user).with_context(import_file=True).load(fields, rows)

    def _import(self, fields, rows):
        result = self._load(fields, rows)
        self.assertFalse(
            [message for message in result["messages"] if message["type"] == "error"],
            result["messages"],
        )
        return result

    def _quants(self, product=None):
        return self.env["stock.quant"].search(
            [
                ("product_id", "=", (product or self.product).id),
                ("location_id", "=", self.location.id),
            ]
        )

    def test_import_replaces_the_counted_quantity(self):
        self._import(
            ["product_id", "location_id", "inventory_quantity"],
            [[self.product.name, self.location.complete_name, "4"]],
        )
        quant = self._quants()
        self.assertEqual(len(quant), 1, "the count must land on the existing line")
        quant.action_apply_inventory()
        self.assertEqual(quant.quantity, 4, "10 counted as 4 must end up as 4, not as 14")

    def test_import_zero_empties_the_line(self):
        self._import(
            ["product_id", "location_id", "inventory_quantity"],
            [[self.product.name, self.location.complete_name, "0"]],
        )
        quant = self._quants()
        self.assertTrue(quant.inventory_quantity_set, "a counted 0 is a count, not an empty cell")
        quant.action_apply_inventory()
        self.assertEqual(quant.quantity, 0)

    def test_import_creates_the_line_when_there_is_none(self):
        other = self.env["product.product"].create({"name": "Uncounted Product", "is_storable": True})
        self._import(
            ["product_id", "location_id", "inventory_quantity"],
            [[other.name, self.location.complete_name, "7"]],
        )
        quant = self._quants(other)
        self.assertEqual(len(quant), 1)
        quant.action_apply_inventory()
        self.assertEqual(quant.quantity, 7)

    def test_import_matches_the_lot_of_the_row_product(self):
        """A lot name is only unique per product: the importer resolves it to whichever
        product's lot comes first, so the match has to re-point it."""
        tracked = self.env["product.product"].create(
            {
                "name": "Tracked Product",
                "is_storable": True,
                "tracking": "lot",
            }
        )
        homonym = self.env["product.product"].create(
            {
                "name": "Homonym Lot Product",
                "is_storable": True,
                "tracking": "lot",
            }
        )
        self.env["stock.lot"].create({"name": "L1", "product_id": homonym.id})
        lot = self.env["stock.lot"].create({"name": "L1", "product_id": tracked.id})
        self.env["stock.quant"]._update_available_quantity(tracked, self.location, 10, lot_id=lot)

        self._import(
            ["product_id", "location_id", "lot_id", "inventory_quantity"],
            [[tracked.name, self.location.complete_name, "L1", "4"]],
        )
        quant = self._quants(tracked)
        self.assertEqual(len(quant), 1, "the count must land on the lot of this product")
        quant.action_apply_inventory()
        self.assertEqual(quant.quantity, 4)

    def test_import_of_the_on_hand_column_applies_on_the_line(self):
        """The inventoried quantity applies itself, so it has to land on the right line."""
        self._import(
            ["product_id", "location_id", "inventory_quantity_auto_apply"],
            [[self.product.name, self.location.complete_name, "4"]],
        )
        quant = self._quants()
        self.assertEqual(len(quant), 1)
        self.assertEqual(quant.quantity, 4)

    def test_row_without_a_count_leaves_the_line_alone(self):
        """A file with no counted quantity column is not a count of zero."""
        self._import(
            ["product_id", "location_id"],
            [[self.product.name, self.location.complete_name]],
        )
        quant = self._quants()
        self.assertEqual(len(quant), 1, "the row names a line, it does not add one")
        self.assertFalse(quant.inventory_quantity_set, "no row said 0")

    def test_blank_count_leaves_the_line_alone(self):
        """Counting part of an exported file is the ordinary file: the rows left blank
        are not counts of zero."""
        self._import(
            ["product_id", "location_id", "inventory_quantity"],
            [[self.product.name, self.location.complete_name, ""]],
        )
        quant = self._quants()
        self.assertEqual(len(quant), 1)
        self.assertFalse(quant.inventory_quantity_set, "an empty cell is not a counted 0")
        self.assertEqual(quant.quantity, 10, "applying it would have emptied the line")

    def test_two_rows_for_the_same_line_count_it_once(self):
        other = self.env["product.product"].create({"name": "Twice Counted", "is_storable": True})
        self._import(
            ["product_id", "location_id", "inventory_quantity"],
            [
                [other.name, self.location.complete_name, "4"],
                [other.name, self.location.complete_name, "7"],
            ],
        )
        quant = self._quants(other)
        self.assertEqual(len(quant), 1, "both rows are the same stock line")
        quant.action_apply_inventory()
        self.assertEqual(quant.quantity, 7, "the last count of a line wins, it is not added up")

    def test_import_without_the_adjustment_group_changes_nothing(self):
        """Applying a count needs the adjustment group, importing one cannot go around it."""
        plain = new_test_user(self.env, login="plain_stock_user", groups="stock.group_stock_user")

        result = self._load(
            ["product_id", "location_id", "inventory_quantity"],
            [[self.product.name, self.location.complete_name, "4"]],
            user=plain,
        )

        self.assertTrue([message for message in result["messages"] if message["type"] == "error"])
        quant = self._quants()
        self.assertEqual(quant.quantity, 10)
        self.assertFalse(quant.inventory_quantity_set)
