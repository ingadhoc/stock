from dateutil.relativedelta import relativedelta
from odoo import fields
from odoo.tests.common import TransactionCase


class TestRemovalByLocationPriority(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.now = fields.Datetime.now()
        cls.stock_location = cls.env.ref("stock.stock_location_stock")
        cls.priority_strategy = cls.env.ref("stock_removal_by_location_priority.removal_by_location_priority")
        cls.fifo_strategy = cls.env.ref("stock.removal_fifo")
        cls.category = cls.env["product.category"].create(
            {
                "name": "Removal priority test",
                "removal_strategy_id": cls.priority_strategy.id,
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Removal priority test product",
                "is_storable": True,
                "categ_id": cls.category.id,
            }
        )
        # priorities run opposite to the creation order, so priority order and
        # FIFO order are exactly reversed and the asserts tell them apart
        cls.locations = cls.env["stock.location"]
        for priority in (30, 20, 10):
            cls.locations |= cls.env["stock.location"].create(
                {
                    "name": "Removal priority %s" % priority,
                    "location_id": cls.stock_location.id,
                    "usage": "internal",
                    "removal_priority": priority,
                }
            )
        cls.loc_30, cls.loc_20, cls.loc_10 = cls.locations
        for index, location in enumerate(cls.locations):
            cls.env["stock.quant"].create(
                {
                    "product_id": cls.product.id,
                    "location_id": location.id,
                    "quantity": 10,
                    "in_date": cls.now - relativedelta(days=3 - index),
                }
            )

    def _gathered_location_ids(self):
        # recordset equality ignores ordering, so the assert compares id lists
        quants = self.env["stock.quant"]._gather(self.product, self.stock_location)
        return quants.location_id.ids

    def test_removal_order_by_location_priority(self):
        """Removal order follows the location priority.

        Covers: quants are gathered by location removal_priority; raising the
        priority of a location pushes it to the end of the queue; core
        strategies keep their own order.
        """
        with self.subTest("stock leaves the lowest priority location first"):
            self.assertEqual(
                self._gathered_location_ids(),
                [self.loc_10.id, self.loc_20.id, self.loc_30.id],
            )

        with self.subTest("raising a location priority sends it to the end"):
            self.loc_10.removal_priority = 99
            self.assertEqual(
                self._gathered_location_ids(),
                [self.loc_20.id, self.loc_30.id, self.loc_10.id],
            )
            self.loc_10.removal_priority = 10

        with self.subTest("FIFO still orders by incoming date"):
            self.category.removal_strategy_id = self.fifo_strategy
            self.assertEqual(
                self._gathered_location_ids(),
                [self.loc_30.id, self.loc_20.id, self.loc_10.id],
            )
