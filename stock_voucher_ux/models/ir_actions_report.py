##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import io
import logging
import re

from odoo import models

_logger = logging.getLogger(__name__)

try:
    from PyPDF2 import PdfFileReader
except ImportError:  # pragma: no cover
    _logger.debug("PyPDF2 could not be imported; voucher page counting is disabled.")
    PdfFileReader = None


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _get_voucher_copies(self):
        """Copias por hoja que imprime el reporte, para no contar la misma hoja
        más de una vez. Aeroo lo expresa en ``copies`` (entero) y el recibo de
        entrega argentino en ``l10n_ar_copies``."""
        self.ensure_one()
        if self._fields.get("copies") and self.copies:
            return self.copies
        if self._fields.get("l10n_ar_copies"):
            return {"duplicado": 2, "triplicado": 3}.get(self.l10n_ar_copies, 0)
        return 0

    def _count_voucher_pages(self, picking, data=None):
        """Cuántos remitos hay que asignar según las páginas REALES del reporte.

        Renderiza el reporte (todavía sin números) y cuenta las páginas con
        productos, acotadas por las páginas sin copias. Devuelve ``None`` si no se
        pudo renderizar o parsear: preferimos no numerar antes que subnumerar un
        talonario preimpreso con una cantidad inventada.
        """
        self.ensure_one()
        if PdfFileReader is None:
            return None
        try:
            # ``report_pdf_no_attachment`` es imprescindible: sin él este render de
            # conteo se guardaría como adjunto del reporte y, si el reporte tiene
            # ``attachment_use``, toda impresión posterior reusaría ese PDF — que
            # todavía no tiene los números que asignamos justo después.
            content = self.with_context(report_pdf_no_attachment=True)._render(
                self.report_name, picking.ids, data=data
            )[0]
            reader = PdfFileReader(io.BytesIO(content))
            pages_with_products = self._count_pages_with_products(reader, picking)
            copies = self._get_voucher_copies()
            if copies:
                return max(1, min(pages_with_products, int(len(reader.pages) / copies)))
            return max(1, pages_with_products)
        except Exception:  # noqa: BLE001 - cualquier problema de render/parseo -> no numerar
            _logger.warning("No se pudieron contar las páginas del remito de %s", picking.display_name, exc_info=True)
            return None

    def _count_pages_with_products(self, pdf_reader, picking):
        """Cuenta las páginas que realmente tienen productos, matcheando
        identificadores de producto (referencia interna / código de barras) en el
        texto de la página, de forma independiente del idioma."""
        move_lines = picking.move_line_ids or picking.move_ids

        product_identifiers = set()
        for line in move_lines:
            product = line.product_id
            if not product:
                continue
            if product.default_code:
                product_identifiers.add(product.default_code.lower().strip())
            if product.barcode:
                product_identifiers.add(product.barcode.lower().strip())

        pages_with_products = 0
        for page_num in range(len(pdf_reader.pages)):
            try:
                text = pdf_reader.pages[page_num].extract_text()
                if not text:
                    continue
                text_lower = text.lower()
                if product_identifiers and any(pid in text_lower for pid in product_identifiers):
                    has_products = True
                else:
                    # Fallback: patrón numérico genérico (independiente del idioma).
                    has_products = bool(re.search(r"\b\d+[.,]\d+\b", text_lower))
                if has_products:
                    pages_with_products += 1
            except Exception:  # noqa: BLE001 - si no se puede extraer texto asumimos que tiene productos
                pages_with_products += 1

        # Siempre hay al menos una página con productos.
        return max(1, pages_with_products)

    def _get_voucher_copies_from_url(self, url):
        """Copias (campo aeroo ``copies``) del reporte que se imprime,
        resuelto por su ``report_name`` en la URL."""
        marker = "/report/aeroo/"
        if marker not in url:
            return None
        report_name = url.split(marker)[1].split("?")[0].split("/")[0]
        report = self.search([("report_name", "=", report_name)], limit=1)
        return report.copies if report else None
