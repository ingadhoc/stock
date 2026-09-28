from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestRepairButton(TransactionCase):
    """El botón Reparar sale del tipo de operación, no de `return_id`.

    El core lo muestra solo en devoluciones creadas con el asistente "Devolver",
    las únicas que tienen `return_id`.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.picking_type_in = cls.env.ref("stock.picking_type_in")
        cls.picking_type_out = cls.env.ref("stock.picking_type_out")
        # The toggle is only available on a type that receives returns of another one.
        cls.picking_type_out.return_picking_type_id = cls.picking_type_in
        cls.picking_type_in.is_repairable = True

    def _new_receipt(self):
        return self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_in.id,
                "location_id": self.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": self.env.ref("stock.stock_location_stock").id,
            }
        )

    def test_repairable_without_return_id(self):
        picking = self._new_receipt()
        self.assertFalse(picking.return_id)
        self.assertTrue(picking.is_repairable)

    def test_not_repairable_if_type_is_not(self):
        self.picking_type_in.is_repairable = False
        self.assertFalse(self._new_receipt().is_repairable)
