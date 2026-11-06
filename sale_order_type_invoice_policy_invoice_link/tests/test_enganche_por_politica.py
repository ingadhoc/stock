##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests import tagged

from .common import SaleOrderTypeInvoicePolicyInvoiceLinkCommon


@tagged("post_install", "-at_install")
class TestEnganchePorPolitica(SaleOrderTypeInvoicePolicyInvoiceLinkCommon):
    """Cuando la política factura lo pedido, el puente engancha la entrega a la factura.

    El módulo base engancha la factura con el albarán al crear la línea de factura.
    Con una política que factura lo pedido la factura sale antes de la entrega, así
    que cuando la salida se valida ya no hay quién la enganche: eso hace el puente.
    """

    def test_con_nota_de_credito_engancha_la_factura(self):
        """Una salida no es una devolución por tener `to_refund`, que nace en True.

        Lo que la hace devolución es volver del cliente. Mirando solo la marca, una
        venta con nota de crédito enganchaba la entrega a la nota en vez de a la
        factura.
        """
        order = self._order(self._sale_type("order"))
        invoice = self._facturar(order)
        nota = self._nota_credito(invoice)

        self._deliver(order.picking_ids)

        enganchadas = order.picking_ids.move_ids.invoice_line_ids
        self.assertEqual(enganchadas, invoice.invoice_line_ids, "la entrega es de la factura")
        self.assertFalse(enganchadas & nota.invoice_line_ids, "la entrega no es de la nota de crédito")
        self.assert_vinculo_coherente(order)

    def test_la_politica_del_tipo_engancha_la_entrega_a_la_factura(self):
        casos = [
            ("el tipo factura lo pedido", "order", None),
            ("el tipo delega en el producto, que factura lo pedido", "by_product", "product_order"),
        ]
        for etiqueta, politica, producto in casos:
            with self.subTest(etiqueta):
                order = self._order(self._sale_type(politica), product=producto and getattr(self, producto))
                invoice = self._facturar(order)

                self._deliver(order.picking_ids)

                self.assertEqual(
                    order.picking_ids.move_ids.invoice_line_ids,
                    invoice.invoice_line_ids,
                    "la entrega tenía que quedar enganchada a la factura que ya existía",
                )
                self.assert_vinculo_coherente(order)
                self.assert_invariantes(order)

    def test_no_se_engancha_la_factura_de_otra_venta(self):
        otra = self._order(self._sale_type("order"))
        otra_factura = self._facturar(otra)
        order = self._order(self._sale_type("order"))
        invoice = self._facturar(order)

        self._deliver(order.picking_ids)

        enganchadas = order.picking_ids.move_ids.invoice_line_ids
        self.assertEqual(enganchadas, invoice.invoice_line_ids)
        self.assertFalse(
            enganchadas & otra_factura.invoice_line_ids,
            "el puente enganchó una línea de la factura de otra venta",
        )
        self.assert_vinculo_coherente(order)

    def test_con_entregadas_el_puente_no_engancha(self):
        """Con "entregadas" la factura sale después, así que al validar no hay qué enganchar."""
        casos = [
            ("el tipo factura las entregadas", "delivery", None),
            ("el tipo delega en el producto, que factura las entregadas", "by_product", None),
        ]
        for etiqueta, politica, producto in casos:
            with self.subTest(etiqueta):
                order = self._order(self._sale_type(politica), product=producto and getattr(self, producto))

                self._deliver(order.picking_ids)

                self.assertFalse(
                    order.picking_ids.move_ids.invoice_line_ids,
                    "al validar la entrega todavía no hay factura que enganchar",
                )
                self.assert_invariantes(order)
