##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.exceptions import ValidationError
from odoo.tests import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestLocationSecurity(TransactionCase):
    """Un usuario con ubicaciones restringidas solo valida transferencias cuyo
    origen y destino están entre sus ubicaciones permitidas (o sus hijas). La
    restricción vale solo al validar el picking (ticket 109676)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.picking_type = cls.warehouse.int_type_id
        Location = cls.env["stock.location"]
        stock_loc = cls.warehouse.lot_stock_id
        cls.allowed_loc = Location.create({"name": "Zona permitida", "location_id": stock_loc.id})
        cls.allowed_child_loc = Location.create({"name": "Estante permitido", "location_id": cls.allowed_loc.id})
        cls.other_loc = Location.create({"name": "Zona ajena", "location_id": stock_loc.id})
        cls.customer_loc = cls.env.ref("stock.stock_location_customers")
        cls.product = cls.env["product.product"].create({"name": "Producto location_security", "is_storable": True})
        cls.user = cls.env["res.users"].create(
            {
                "name": "Usuario restringido",
                "login": "location_security_user",
                "group_ids": [(6, 0, [cls.env.ref("stock.group_stock_user").id])],
                "restrict_locations": True,
                "stock_location_ids": [(6, 0, [cls.allowed_loc.id, cls.customer_loc.id])],
            }
        )

    def _new_picking(self, location, location_dest, demand=1.0, quantity=1.0):
        """Transferencia confirmada y reservada, con la cantidad hecha cargada."""
        self.env["stock.quant"]._update_available_quantity(self.product, location, demand)
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type.id,
                "location_id": location.id,
                "location_dest_id": location_dest.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": demand,
                            "location_id": location.id,
                            "location_dest_id": location_dest.id,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()
        picking.action_assign()
        picking.move_ids.quantity = quantity
        picking.move_ids.picked = True
        return picking

    def test_validate_picking_location_rights(self):
        """Comportamientos 1 a 5: validar como usuario restringido."""
        with self.subTest("sin el check, valida aunque las ubicaciones no estén permitidas"):
            self.user.restrict_locations = False
            picking = self._new_picking(self.other_loc, self.customer_loc)
            picking.with_user(self.user).button_validate()
            self.assertEqual(picking.state, "done")
            self.user.restrict_locations = True

        with self.subTest("una sububicación de una permitida cuenta como permitida"):
            picking = self._new_picking(self.allowed_child_loc, self.customer_loc)
            picking.with_user(self.user).button_validate()
            self.assertEqual(picking.state, "done")

        with self.subTest("origen no permitido: no valida y el error nombra el picking y la ubicación"):
            picking = self._new_picking(self.other_loc, self.allowed_loc)
            with self.assertRaises(ValidationError) as error:
                picking.with_user(self.user).button_validate()
            self.assertIn(picking.name, str(error.exception))
            self.assertIn(self.other_loc.name, str(error.exception))
            self.assertNotEqual(picking.state, "done")

        with self.subTest("destino no permitido: no valida y el error nombra la ubicación"):
            picking = self._new_picking(self.allowed_loc, self.other_loc)
            with self.assertRaises(ValidationError) as error:
                picking.with_user(self.user).button_validate()
            self.assertIn(self.other_loc.name, str(error.exception))
            self.assertNotEqual(picking.state, "done")

    def test_no_restriction_outside_validation(self):
        """Comportamientos 6 y 7 (ticket 109676): fuera del botón Validar, y
        al cancelar, no se restringe."""
        with self.subTest("un movimiento hecho fuera de Validar no se restringe"):
            self.env["stock.quant"]._update_available_quantity(self.product, self.other_loc, 1.0)
            move = self.env["stock.move"].create(
                {
                    "product_id": self.product.id,
                    "product_uom_qty": 1.0,
                    "location_id": self.other_loc.id,
                    "location_dest_id": self.customer_loc.id,
                }
            )
            move._action_confirm()
            move._action_assign()
            move.quantity = 1.0
            move.picked = True
            move.with_user(self.user)._action_done()
            self.assertEqual(move.state, "done")

        with self.subTest("cancelar un movimiento durante la validación no se restringe"):
            picking = self._new_picking(self.other_loc, self.allowed_loc)
            picking.move_ids.with_user(self.user).with_context(button_validate_picking_ids=picking.ids)._action_cancel()
            self.assertEqual(picking.move_ids.state, "cancel")

    def test_backorder_wizard_keeps_restriction(self):
        """Comportamiento 8: validar parcial pasa por el asistente de backorder,
        y la restricción tiene que seguir aplicando al procesarlo."""
        for method in ("process", "process_cancel_backorder"):
            with self.subTest("permitido: el asistente procesa", method=method):
                picking = self._new_picking(self.allowed_loc, self.customer_loc, demand=2.0)
                action = picking.with_user(self.user).button_validate()
                wizard = Form.from_action(self.env(user=self.user), action).save()
                getattr(wizard, method)()
                self.assertEqual(picking.state, "done")

            with self.subTest("no permitido: el asistente no procesa", method=method):
                picking = self._new_picking(self.other_loc, self.customer_loc, demand=2.0)
                action = picking.with_user(self.user).button_validate()
                wizard = Form.from_action(self.env(user=self.user), action).save()
                with self.assertRaises(ValidationError):
                    getattr(wizard, method)()
                self.assertNotEqual(picking.state, "done")
