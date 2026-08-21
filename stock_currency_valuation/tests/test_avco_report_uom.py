from freezegun import freeze_time
from odoo import Command

from .common import TestStockCurrencyValuationCommon


class TestAvcoReportUom(TestStockCurrencyValuationCommon):
    """La cantidad del reporte de auditoría AVCO va en la UoM de REFERENCIA del
    producto, no en la del movimiento.

    Regresión: la vista SQL de este módulo es una copia de la del core, y la copia
    había perdido la conversión ``sm.quantity * (um.factor / up.factor)`` junto con
    los dos JOIN sobre ``uom_uom``. Con el módulo instalado, una recepción de 1
    docena informaba cantidad 1 en vez de 12, y como el reporte calcula el costo
    unitario como ``total_value / total_quantity``, el AVCO salía 12 veces más caro.
    """

    def _receipt_in_uom(self, qty, uom, date_str):
        """Recepción validada expresada en `uom`, que puede no ser la del producto."""
        with freeze_time(date_str):
            picking = self.env["stock.picking"].create(
                {
                    "partner_id": self.vendor.id,
                    "picking_type_id": self.picking_type_in.id,
                    "location_id": self.supplier_location.id,
                    "location_dest_id": self.stock_location.id,
                    "move_ids": [
                        Command.create(
                            {
                                "product_id": self.product.id,
                                "product_uom_qty": qty,
                                "product_uom": uom.id,
                                "location_id": self.supplier_location.id,
                                "location_dest_id": self.stock_location.id,
                            }
                        )
                    ],
                }
            )
            picking.action_confirm()
            move = picking.move_ids
            move.quantity = qty
            move.picked = True
            picking.button_validate()
            self.assertEqual(picking.state, "done")
            return picking, move

    def _report_line(self, move):
        line = (
            self.env["stock.avco.report"]
            .with_company(self.company)
            .search([("product_id", "=", self.product.id), ("res_model_name", "=", "stock.move")])
            .filtered(lambda r: r.id == move.id)
        )
        self.assertEqual(len(line), 1, "Se esperaba una línea del reporte para el movimiento.")
        return line

    def test_avco_report_quantity_in_product_uom(self):
        uom_dozen = self.env.ref("uom.product_uom_dozen")
        self.assertNotEqual(uom_dozen, self.product.uom_id, "El test necesita una UoM distinta a la del producto.")

        self.product.standard_price = 100.0
        _picking, move = self._receipt_in_uom(1, uom_dozen, self.DAY_1)

        line = self._report_line(move)
        # El oráculo es la conversión del propio ORM: la cantidad del reporte tiene que
        # estar en la UoM de referencia del producto, no en la del movimiento.
        expected = uom_dozen._compute_quantity(1, self.product.uom_id)
        self._assert_almost(line.quantity, expected)
        self.assertNotAlmostEqual(
            line.quantity, 1.0, places=2, msg="La cantidad quedó en la UoM del movimiento, sin convertir."
        )

    def test_avco_report_unit_cost_uses_converted_quantity(self):
        uom_dozen = self.env.ref("uom.product_uom_dozen")
        self.product.standard_price = 100.0
        _picking, move = self._receipt_in_uom(1, uom_dozen, self.DAY_1)

        line = self._report_line(move)
        # Consecuencia de la conversión: el costo unitario se calcula sobre la cantidad
        # convertida. Se compara contra los propios valores del reporte para no depender
        # de cómo se valorizó la recepción.
        self._assert_almost(line.avco_value, line.total_value / line.total_quantity)
        self._assert_almost(line.total_quantity, uom_dozen._compute_quantity(1, self.product.uom_id))
