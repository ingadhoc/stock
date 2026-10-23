##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPickingLabels(TransactionCase):
    """The ZPL 5 x 2,5 cm label from a picking prints the quantity per line, and with
    Print Packaging the native logic: Copies labels per move."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {"name": "Label Product", "is_storable": True, "barcode": "LBL0001"}
        )
        picking_type = cls.env.ref("stock.picking_type_in")
        cls.picking = cls.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product.id,
                            "product_uom_qty": 3,
                            "location_id": picking_type.default_location_src_id.id,
                            "location_dest_id": picking_type.default_location_dest_id.id,
                        },
                    )
                ],
            }
        )
        cls.picking.action_confirm()
        cls.picking.move_ids.quantity = 3

    def _labels(self, **vals):
        wizard = (
            self.env["product.label.layout"]
            .with_context(active_model="stock.picking", active_ids=self.picking.ids)
            .create({"zpl_template": "zpl_5x25", "move_quantity": "custom", **vals})
        )
        zpl = self.env["ir.actions.report"]._render_qweb_text(
            "stock_ux.action_custom_barcode_transfer_template_view_zpl", wizard.ids
        )[0]
        return zpl.decode().count("^FDLBL0001^FS")

    def test_quantity_per_line(self):
        self.assertEqual(self._labels(custom_quantity=1), 3)

    def test_print_packaging_uses_copies(self):
        self.assertEqual(self._labels(custom_quantity=1, print_packaging=True), 1)
