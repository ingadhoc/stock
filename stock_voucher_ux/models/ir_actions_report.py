##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _get_voucher_copies_from_url(self, url):
        """Copias (campo aeroo ``copies``) del reporte que se imprime,
        resuelto por su ``report_name`` en la URL."""
        marker = "/report/aeroo/"
        if marker not in url:
            return None
        report_name = url.split(marker)[1].split("?")[0].split("/")[0]
        report = self.search([("report_name", "=", report_name)], limit=1)
        return report.copies if report else None
