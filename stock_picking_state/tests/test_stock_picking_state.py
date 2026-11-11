##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from lxml import etree
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestStockPickingState(TransactionCase):
    """Asignación del subestado según el estado y el tipo de operación del
    traslado, y lo que se ve en el formulario (tarea 76489)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Detail = cls.env["stock.picking.state_detail"]
        # los de la data demo o de la base no deben interferir con los del test
        cls.Detail.search([]).action_archive()
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.picking_type_out = cls.warehouse.out_type_id
        cls.stock_loc = cls.picking_type_out.default_location_src_id
        cls.customer_loc = cls.env.ref("stock.stock_location_customers")
        cls.product = cls.env["product.product"].create({"name": "Producto 76489", "is_storable": True})
        cls.env["stock.quant"]._update_available_quantity(cls.product, cls.stock_loc, 10)
        cls.in_draft = cls.Detail.create({"name": "En armado", "state": "draft", "picking_type": "outgoing"})
        cls.to_authorize = cls.Detail.create(
            {"name": "Esperando autorización", "state": "assigned", "picking_type": "outgoing", "sequence": 10}
        )
        cls.authorized = cls.Detail.create(
            {"name": "Autorizado", "state": "assigned", "picking_type": "outgoing", "sequence": 10}
        )

    def _new_delivery(self):
        return self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_out.id,
                "location_id": self.stock_loc.id,
                "location_dest_id": self.customer_loc.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1,
                            "location_id": self.stock_loc.id,
                            "location_dest_id": self.customer_loc.id,
                        },
                    )
                ],
            }
        )

    def test_assigns_first_detail_in_list_order(self):
        """Con dos subestados de igual secuencia, el traslado toma el primero
        de la lista aunque el otro se haya editado después."""
        self.to_authorize.write({"name": "Esperando autorización (editado)"})
        self.env.flush_all()
        details = self.Detail.search([("state", "=", "assigned"), ("picking_type", "=", "outgoing")])
        self.assertEqual(details[0], self.to_authorize)
        picking = self._new_delivery()
        self.assertEqual(picking.state_detail_id, self.in_draft)
        picking.action_confirm()
        picking.action_assign()
        self.assertEqual(picking.state, "assigned")
        self.assertEqual(picking.state_detail_id, self.to_authorize)

    def test_keeps_valid_detail_and_resets_when_status_changes(self):
        picking = self._new_delivery()
        picking.action_confirm()
        picking.action_assign()
        picking.state_detail_id = self.authorized
        picking.move_ids.quantity = 1
        picking.move_ids.picked = True
        self.assertEqual(picking.state_detail_id, self.authorized)
        picking.button_validate()
        self.assertEqual(picking.state, "done")
        self.assertFalse(picking.state_detail_id)

    def test_detail_of_another_status_is_rejected(self):
        picking = self._new_delivery()
        with self.assertRaises(ValidationError):
            picking.state_detail_id = self.authorized
            self.env.flush_all()

    def test_archived_detail_is_not_assigned(self):
        self.in_draft.action_archive()
        picking = self._new_delivery()
        self.assertFalse(picking.state_detail_id)

    def test_form_shows_selector_without_detail(self):
        """El selector se ve aunque el traslado todavía no tenga subestado
        (por ejemplo, uno creado antes de configurarlos)."""
        arch = self.env["stock.picking"].get_views([(False, "form")])["views"]["form"]["arch"]
        field = etree.fromstring(arch).xpath("//field[@name='state_detail_id']")
        self.assertTrue(field)
        self.assertNotIn("invisible", field[0].attrib)
