##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBlockManualLinesLot(TransactionCase):
    """With "Block force availability", a line can only take a serial from the location that
    holds it: Odoo reserves nothing for a serial that is not there, so the product total alone
    let it through and validating left the serial negative."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids += cls.env.ref("stock.group_stock_manager")
        cls.stock = cls.env.ref("stock.stock_location_stock")
        cls.shelf = cls.env["stock.location"].create({"name": "Shelf", "location_id": cls.stock.id})
        cls.output = cls.env["stock.location"].create(
            {"name": "Output", "location_id": cls.stock.warehouse_id.view_location_id.id}
        )
        cls.picking_type = cls.env.ref("stock.picking_type_internal")
        cls.picking_type.block_manual_lines = True
        # on by default and unrelated: it would refuse the manual line for exceeding the demand
        cls.picking_type.block_additional_quantity = False
        cls.product = cls.env["product.product"].create(
            {"name": "Serial Product", "is_storable": True, "tracking": "serial"}
        )
        cls.lot_on_shelf = cls.env["stock.lot"].create({"name": "SN-SHELF", "product_id": cls.product.id})
        cls.lot_elsewhere = cls.env["stock.lot"].create({"name": "SN-GONE", "product_id": cls.product.id})
        cls.env["stock.quant"]._update_available_quantity(cls.product, cls.shelf, 1, lot_id=cls.lot_on_shelf)

    def _create_picking(self):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type.id,
                "location_id": self.stock.id,
                "location_dest_id": self.output.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1,
                            "location_id": self.stock.id,
                            "location_dest_id": self.output.id,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()
        # confirming reserves the serial on the shelf; each test adds its own line
        picking.do_unreserve()
        return picking

    def _create_line(self, picking, lot, location):
        return self.env["stock.move.line"].create(
            {
                "move_id": picking.move_ids.id,
                "picking_id": picking.id,
                "product_id": self.product.id,
                "product_uom_id": self.product.uom_id.id,
                "location_id": location.id,
                "location_dest_id": self.output.id,
                "lot_id": lot.id,
                "quantity": 1,
            }
        )

    def _on_hand(self, location, lot):
        quants = self.env["stock.quant"]._gather(self.product, location, lot_id=lot, strict=True)
        return sum(quants.mapped("quantity"))

    def test_serial_held_by_no_location_is_refused(self):
        picking = self._create_picking()
        with self.assertRaisesRegex(ValidationError, "SN-GONE"):
            self._create_line(picking, self.lot_elsewhere, self.stock)

    def test_serial_held_by_a_sublocation_is_refused_from_the_parent(self):
        """Validating would take it from the parent, where it is not."""
        picking = self._create_picking()
        with self.assertRaisesRegex(ValidationError, "SN-SHELF"):
            self._create_line(picking, self.lot_on_shelf, self.stock)

    def test_serial_is_taken_from_the_location_that_holds_it(self):
        picking = self._create_picking()
        line = self._create_line(picking, self.lot_on_shelf, self.shelf)
        self.assertEqual(line.location_id, self.shelf)

    def test_negative_quant_without_lot_does_not_hide_the_serial(self):
        """Odoo skips negative quants without lot when it takes the serial out."""
        self.env["stock.quant"]._update_available_quantity(self.product, self.shelf, -3)
        # keep the product total positive, so only the lot check is at stake
        self.env["stock.quant"]._update_available_quantity(self.product, self.stock, 5)
        picking = self._create_picking()
        line = self._create_line(picking, self.lot_on_shelf, self.shelf)
        self.assertEqual(line.lot_id, self.lot_on_shelf)

    def test_switching_the_line_to_a_serial_without_stock_is_refused(self):
        picking = self._create_picking()
        line = self._create_line(picking, self.lot_on_shelf, self.shelf)
        with self.assertRaisesRegex(ValidationError, "SN-GONE"):
            line.write({"lot_id": self.lot_elsewhere.id})

    def test_done_line_can_be_moved_to_the_location_that_holds_the_serial(self):
        """The fix for a line validated from the wrong location must keep working."""
        self.picking_type.block_manual_lines = False
        picking = self._create_picking()
        line = self._create_line(picking, self.lot_on_shelf, self.stock)
        picking.move_ids.picked = True
        picking._action_done()
        self.assertEqual(self._on_hand(self.stock, self.lot_on_shelf), -1)

        self.picking_type.block_manual_lines = True
        picking.is_locked = False
        line.write({"location_id": self.shelf.id})
        self.assertEqual(self._on_hand(self.stock, self.lot_on_shelf), 0)
        self.assertEqual(self._on_hand(self.shelf, self.lot_on_shelf), 0)

    def test_operation_types_without_the_block_are_not_affected(self):
        self.picking_type.block_manual_lines = False
        picking = self._create_picking()
        line = self._create_line(picking, self.lot_elsewhere, self.stock)
        self.assertEqual(line.lot_id, self.lot_elsewhere)
