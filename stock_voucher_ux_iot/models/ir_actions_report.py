##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


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
            # The document is already on its way to the printer, so when the page
            # count cannot be determined we still assign a single voucher instead
            # of letting the paper come out unnumbered.
            number_of_pages = self._count_voucher_pages(picking, data=data) or 1
            picking.assign_numbers(number_of_pages, book)
            picking.env.flush_all()
