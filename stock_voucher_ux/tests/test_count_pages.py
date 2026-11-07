##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests.common import TransactionCase


class _FakePage:
    def __init__(self, text):
        self._text = text

    def extract_text(self):
        return self._text


class _FakeReader:
    """Reemplazo duck-typed de ``PyPDF2.PdfFileReader`` para no renderizar un PDF."""

    def __init__(self, texts):
        self.pages = [_FakePage(text) for text in texts]


class TestVoucherPageCount(TransactionCase):
    """Sólo las páginas con productos consumen un número de remito."""

    def _picking(self, *default_codes):
        products = self.env["product.product"].create(
            [
                {"name": "Producto remito test %s" % index, "type": "consu", "default_code": code}
                for index, code in enumerate(default_codes)
            ]
        )
        location = self.env.ref("stock.stock_location_stock")
        location_dest = self.env.ref("stock.stock_location_customers")
        return self.env["stock.picking"].create(
            {
                "picking_type_id": self.env.ref("stock.picking_type_out").id,
                "location_id": location.id,
                "location_dest_id": location_dest.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "name": product.name,
                            "product_id": product.id,
                            "product_uom_qty": 1.0,
                            "product_uom": product.uom_id.id,
                            "location_id": location.id,
                            "location_dest_id": location_dest.id,
                        },
                    )
                    for product in products
                ],
            }
        )

    def test_page_without_products_does_not_consume_a_voucher(self):
        # Segunda hoja: sólo el encabezado repetido, sin líneas, con un decimal
        # en el domicilio ("Km 1,4") — el caso del ticket 126294.
        reader = _FakeReader(
            [
                "1,00 UNIDAD TESTPROD [TESTPROD] Producto remito test",
                "Cliente SRL - Ruta Provincial 4 Km 1,4 - Ciudad",
            ]
        )
        self.assertEqual(
            self._picking("TESTPROD")._count_pages_with_products(reader),
            1,
            "Una hoja que sólo repite el encabezado no lleva productos: no debe consumir remito.",
        )
        # Sin código que reconocer se sigue adivinando por el decimal.
        self.assertEqual(self._picking(False)._count_pages_with_products(reader), 2)
        # Y si el reporte no imprime el código, las hojas con líneas siguen contando.
        sin_codigo = _FakeReader(["Producto remito test 1,00 UNIDAD", "Producto remito test 2,00 UNIDAD"])
        self.assertEqual(
            self._picking("TESTPROD")._count_pages_with_products(sin_codigo),
            2,
            "Si el código no aparece en ninguna hoja, no se puede usar para descartar hojas.",
        )
        # Y si alguna línea no tiene código, tampoco: una hoja con sólo esas líneas
        # se descartaría y saldría impresa sin número.
        self.assertEqual(self._picking("TESTPROD", False)._count_pages_with_products(reader), 2)
