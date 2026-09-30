from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("stock_ux_quant_import")
class TestQuantImportLots(TransactionCase):
    """Counting a warehouse turns up lots Odoo does not have yet, and the count has to
    load anyway."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids += cls.env.ref("stock.group_stock_manager")
        cls.env.user.group_ids += cls.env.ref("stock_ux.group_stock_inventory_adjustment")
        cls.location = cls.env.ref("stock.stock_location_stock")
        cls.product = cls.env["product.product"].create(
            {
                "name": "Tracked Product",
                "is_storable": True,
                "tracking": "lot",
            }
        )

    def _import(self, rows):
        result = (
            self.env["stock.quant"]
            .with_context(import_file=True)
            .load(["product_id", "location_id", "lot_id", "inventory_quantity"], rows)
        )
        self.assertFalse(
            [message for message in result["messages"] if message["type"] == "error"],
            result["messages"],
        )
        return result

    def _lots(self, name):
        return self.env["stock.lot"].search(
            [
                ("name", "=", name),
                ("product_id", "=", self.product.id),
            ]
        )

    def test_a_lot_the_count_brings_is_created(self):
        self._import([[self.product.name, self.location.complete_name, "NEW-LOT", "5"]])

        lot = self._lots("NEW-LOT")
        self.assertEqual(len(lot), 1, "the count names a lot Odoo did not have")
        quant = self.env["stock.quant"].search([("lot_id", "=", lot.id)])
        self.assertEqual(quant.inventory_quantity, 5)

    def test_the_same_new_lot_on_two_rows_is_one_lot(self):
        self._import(
            [
                [self.product.name, self.location.complete_name, "NEW-LOT", "5"],
                [self.product.name, self.location.complete_name, "NEW-LOT", "5"],
            ]
        )

        self.assertEqual(len(self._lots("NEW-LOT")), 1)
