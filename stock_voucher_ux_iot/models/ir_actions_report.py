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
    _logger.debug("PyPDF2 could not be imported; voucher page counting will fall back to 1.")
    PdfFileReader = None


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def render_and_send(self, devices, res_ids, data=None, print_id=0, websocket=True):
        """Assign the preprinted voucher numbers when the remito is printed
        through an IoT printer.

        On the regular (browser download) flow the numbers are assigned by
        ``stock_voucher_ux``'s ``/report/download`` controller. The IoT path
        never reaches that controller: the client handler
        (``iot/static/src/iot_report_action.js``) calls this method and
        short-circuits the action, so the document is rendered server-side and
        streamed straight to the printer. We assign the numbers *before*
        delegating to ``super()`` so the render it performs already carries
        them, mirroring the download flow.
        """
        if self._is_preprinted_voucher_report():
            self._assign_preprinted_voucher_numbers(res_ids, data=data)
        return super().render_and_send(devices, res_ids, data=data, print_id=print_id, websocket=websocket)

    def _is_preprinted_voucher_report(self):
        """The remito preimpreso is an aeroo report on ``stock.picking`` whose
        ``report_name`` contains ``remito`` (same guard the download controller
        uses)."""
        self.ensure_one()
        return self.model == "stock.picking" and self.report_type == "aeroo" and "remito" in (self.report_name or "")

    def _assign_preprinted_voucher_numbers(self, res_ids, data=None):
        """Assign voucher numbers to every preprinted picking in ``res_ids``
        that still has none, based on the real number of rendered pages."""
        self.ensure_one()
        for picking in self.env["stock.picking"].browse(res_ids):
            book = picking.book_id
            # Only preprinted books (autoprinted=False) are numbered at print
            # time; autoprinted books are numbered on validation. Skip pickings
            # that already have numbers to keep this idempotent (a retry of the
            # print must not burn extra sequence numbers).
            if not book or book.autoprinted or picking.voucher_ids:
                continue
            number_of_pages = self._count_voucher_pages(picking, data=data)
            picking.assign_numbers(number_of_pages, book)
            picking.env.flush_all()

    def _count_voucher_pages(self, picking, data=None):
        """Render the report once (numbers not assigned yet) and count the real
        number of pages that contain products, capped by the page count without
        copies. Falls back to a single voucher when the output cannot be parsed
        as a multi-page PDF (e.g. ``.doc`` output)."""
        self.ensure_one()
        if PdfFileReader is None:
            return 1
        try:
            content = self._render(self.report_name, picking.ids, data=data)[0]
            reader = PdfFileReader(io.BytesIO(content))
            pages_with_products = self._count_pages_with_products(reader, picking)
            copies = self.copies or 0
            if copies:
                total_pages = int(len(reader.pages) / copies)
                return max(1, min(pages_with_products, total_pages))
            return max(1, pages_with_products)
        except Exception:  # noqa: BLE001 - any render/parse issue -> single voucher
            return 1

    def _count_pages_with_products(self, pdf_reader, picking):
        """Count the pages that actually contain products by matching product
        identifiers (internal reference / barcode) in the page text, in a
        language independent way. Mirrors the logic used by the download
        controller in ``stock_voucher_ux``."""
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
                    # Fallback: generic numeric pattern (language independent).
                    has_products = bool(re.search(r"\b\d+[.,]\d+\b", text_lower))
                if has_products:
                    pages_with_products += 1
            except Exception:  # noqa: BLE001 - if text can't be extracted assume it has products
                pages_with_products += 1

        # There is always at least one page with products.
        return max(1, pages_with_products)
