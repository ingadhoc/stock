##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import SaleOrderTypeInvoicePolicyInvoiceLinkCommon


@tagged("post_install", "-at_install")
class TestGuardaCantidad(SaleOrderTypeInvoicePolicyInvoiceLinkCommon):
    """Un movimiento ya facturado no cambia de cantidad, salvo que el contexto lo habilite.

    La guarda es del módulo base, pero el puente reemplaza su `write`, así que si no
    la repitiera se perdería sin que nada falle.
    """

    def test_no_se_cambia_la_cantidad_de_un_movimiento_facturado(self):
        order = self._order(self._sale_type("order"))
        self._facturar(order)
        self._deliver(order.picking_ids)
        move = order.picking_ids.move_ids
        self.assertTrue(move.invoice_line_ids, "el escenario necesita el movimiento ya enganchado")

        with self.subTest("cambiar la cantidad de un movimiento facturado se rechaza"):
            with self.assertRaises(UserError):
                move.write({"product_uom_qty": 5.0})

        with self.subTest("con el contexto de excepción la cantidad se puede cambiar"):
            move.with_context(bypass_stock_move_update_restriction=True).write({"product_uom_qty": 5.0})
            self.assertEqual(move.product_uom_qty, 5.0)

        self.assert_vinculo_coherente(order)
