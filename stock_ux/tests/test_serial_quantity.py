##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSerialQuantity(TransactionCase):
    """Our constraint on the move quantity used to be named ``_check_quantity``, which is
    core's own method: core calls it to guard that a serial number holds a single unit, and
    the override swallowed it."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids += cls.env.ref("stock.group_stock_manager")
        cls.location = cls.env.ref("stock.stock_location_stock")
        cls.customers = cls.env.ref("stock.stock_location_customers")
        cls.serial_product = cls.env["product.product"].create(
            {
                "name": "Serial Product",
                "is_storable": True,
                "tracking": "serial",
            }
        )
        cls.lot = cls.env["stock.lot"].create({"name": "SN-1", "product_id": cls.serial_product.id})
        # The rule of the module has nothing to do with tracking: a plain product keeps
        # that scenario down to one mechanism.
        cls.plain_product = cls.env["product.product"].create(
            {
                "name": "Plain Product",
                "is_storable": True,
            }
        )

    def test_an_inventory_count_cannot_put_two_units_on_a_serial(self):
        quant = (
            self.env["stock.quant"]
            .with_context(inventory_mode=True)
            .create(
                {
                    "product_id": self.serial_product.id,
                    "location_id": self.location.id,
                    "lot_id": self.lot.id,
                    "inventory_quantity": 5,
                }
            )
        )

        with self.assertRaises(ValidationError) as error:
            quant.action_apply_inventory()
        # Naming the serial is what tells core's guard from the rule of the module, which
        # must not refuse an adjustment: it has no operation type.
        self.assertIn(self.lot.name, str(error.exception))

    def test_a_transfer_still_cannot_exceed_the_initial_demand(self):
        """The constraint of the module keeps working under its own name."""
        picking_type = self.env.ref("stock.picking_type_out")
        picking_type.block_additional_quantity = True
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": self.location.id,
                "location_dest_id": self.customers.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.plain_product.id,
                            "product_uom_qty": 1,
                            "location_id": self.location.id,
                            "location_dest_id": self.customers.id,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()

        with self.assertRaises(ValidationError) as error:
            picking.move_ids.quantity = 2
        self.assertIn("initial demand", str(error.exception))
