##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import io
from unittest.mock import patch

from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


class TestRemitoPreimpresoNumbering(TransactionCase):
    """Numeración de remitos según el tipo de talonario.

    Preimpreso (``autoprinted=False``): NUNCA se numera por la estimación
    ``lines_per_voucher`` (subnumera). La cantidad sale de las páginas reales del
    reporte. Si el tipo de operación pide imprimir al validar
    (``auto_print_delivery_slip``) se numera en la validación, renderizando y
    contando server-side, para no depender de que un cliente web ejecute la acción
    de reporte; si no se pueden contar las páginas no se numera y queda para el
    camino de impresión (controller / IoT).

    Autoimpreso (``autoprinted=True``): se numera en la validación sólo si el
    tipo de operación pide imprimir el remito al validar
    (``auto_print_delivery_slip``) — el remito reemplaza al recibo de entrega
    nativo. Sin ese flag no se numera al validar (se asigna al imprimir a mano).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sequence = cls.env["ir.sequence"].create(
            {
                "name": "Test stock voucher",
                "code": "stock.voucher",
                "prefix": "0001-",
                "padding": 8,
                "implementation": "no_gap",
            }
        )
        cls.book_pre = cls.env["stock.book"].create(
            {
                "name": "Preimpreso test",
                "sequence_id": cls.sequence.id,
                "lines_per_voucher": 25,
                "autoprinted": False,
            }
        )
        cls.book_auto = cls.env["stock.book"].create(
            {
                "name": "Autoimpreso test",
                "sequence_id": cls.sequence.id,
                "lines_per_voucher": 0,
                "autoprinted": True,
            }
        )
        # Consumible no almacenable: la validación no requiere stock disponible.
        cls.product = cls.env["product.product"].create(
            {
                "name": "Producto remito test",
                "type": "consu",
                "default_code": "REMTEST1",
            }
        )
        cls.src = cls.env.ref("stock.stock_location_stock")
        cls.dest = cls.env.ref("stock.stock_location_customers")

    def _make_done_picking(self, book, auto_print=False):
        picking_type = self.env.ref("stock.picking_type_out")
        picking_type.write(
            {
                "book_required": True,
                "book_id": book.id,
                "voucher_required": False,
                "auto_print_delivery_slip": auto_print,
            }
        )
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": self.src.id,
                "location_dest_id": self.dest.id,
                "book_id": book.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "name": self.product.name,
                            "product_id": self.product.id,
                            "product_uom_qty": 1.0,
                            "product_uom": self.product.uom_id.id,
                            "location_id": self.src.id,
                            "location_dest_id": self.dest.id,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
        picking.with_context(skip_sms=True).button_validate()
        return picking

    def test_preprinted_not_preassigned_on_validation(self):
        picking = self._make_done_picking(self.book_pre)
        self.assertEqual(picking.state, "done")
        self.assertFalse(
            picking.voucher_ids,
            "Un talonario preimpreso no debe pre-numerarse por estimación en _action_done; "
            "la numeración se hace al imprimir según páginas reales.",
        )

    def test_autoprinted_assigned_on_validation_with_flag(self):
        # Con auto_print_delivery_slip el remito reemplaza al recibo de entrega
        # y el autoimpreso se numera al validar.
        picking = self._make_done_picking(self.book_auto, auto_print=True)
        self.assertEqual(picking.state, "done")
        self.assertEqual(
            len(picking.voucher_ids),
            1,
            "Un talonario autoimpreso debe asignar un único remito en la validación "
            "cuando el tipo de operación tiene auto_print_delivery_slip.",
        )

    def _pdf_with_pages(self, pages):
        """PDF de ``pages`` páginas, cada una con el código del producto, para que
        el conteo de páginas con productos sea determinístico (no dependemos de
        wkhtmltopdf ni de LibreOffice para renderizar el remito de verdad)."""
        buff = io.BytesIO()
        pdf = canvas.Canvas(buff, pagesize=A4)
        for _page in range(pages):
            pdf.drawString(100, 700, "%s x 1,00" % self.product.default_code)
            pdf.showPage()
        pdf.save()
        return buff.getvalue()

    def test_preprinted_numbered_on_validation_with_flag(self):
        # Ticket 124899: con auto_print_delivery_slip la validación tiene que dejar
        # el remito numerado, y con un número por página real. Antes del fix
        # do_print_and_assign marcaba printed=True y devolvía la acción de reporte:
        # el número lo asignaba recién el controller /report/download cuando un
        # cliente web ejecutaba esa acción. Si valida una automatización
        # server-side (la del tipo de pedido de venta, que descarta el retorno) el
        # picking quedaba done, printed y SIN número.
        report_cls = type(self.env["ir.actions.report"])
        pdf = self._pdf_with_pages(2)
        render_context = {}

        def _fake_render(report, *args, **kwargs):
            render_context.update(report.env.context)
            return (pdf, "pdf")

        with patch.object(report_cls, "_render", autospec=True, side_effect=_fake_render):
            picking = self._make_done_picking(self.book_pre, auto_print=True)
        self.assertEqual(picking.state, "done")
        self.assertTrue(
            render_context.get("report_pdf_no_attachment"),
            "El render de conteo no se debe guardar como adjunto: con attachment_use, "
            "toda impresión posterior reusaría ese PDF, que todavía no tiene números.",
        )
        self.assertEqual(
            len(picking.voucher_ids),
            2,
            "Con auto_print_delivery_slip el talonario preimpreso debe quedar numerado en "
            "la validación, con un remito por página real del reporte, sin depender de que "
            "un cliente web ejecute la acción que devuelve button_validate.",
        )

    # El aviso de que no se pudieron contar las páginas es justo lo que este test
    # provoca, así que lo silenciamos: si no, el traceback ensucia el log y runbot
    # marca la build en rojo aunque los tests pasen.
    @mute_logger("odoo.addons.stock_voucher_ux.models.ir_actions_report")
    def test_preprinted_not_numbered_when_pages_cannot_be_counted(self):
        # Si el reporte no se puede renderizar o parsear como PDF (p. ej. devuelve
        # HTML), no inventamos una cantidad: preferimos no numerar y dejar el número
        # al camino de impresión, antes que subnumerar un talonario preimpreso.
        report_cls = type(self.env["ir.actions.report"])
        with patch.object(report_cls, "_render", return_value=(b"<!DOCTYPE html><html></html>", "html")):
            picking = self._make_done_picking(self.book_pre, auto_print=True)
        self.assertEqual(picking.state, "done")
        self.assertFalse(
            picking.voucher_ids,
            "Sin páginas reales no se debe numerar el talonario preimpreso en la validación.",
        )

    def test_autoprinted_not_assigned_without_flag(self):
        # Sin el flag, validar no numera: el número se asigna al imprimir a mano.
        picking = self._make_done_picking(self.book_auto, auto_print=False)
        self.assertEqual(picking.state, "done")
        self.assertFalse(
            picking.voucher_ids,
            "Sin auto_print_delivery_slip, un talonario autoimpreso no debe numerarse "
            "en la validación; el número se asigna al imprimir.",
        )
