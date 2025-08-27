# Copyright 2025 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _attach_sign(self):
        """
        Attach signed delivery slip to the picking.

        This override ensures that if a substitution report is defined
        for the delivery slip, it is used instead of the native report.
        Otherwise, it falls back to the standard Odoo behavior.
        """
        self.ensure_one()

        # Get the native delivery report
        delivery_report = self.env.ref("stock.action_report_delivery")

        # Check if there's a substitution report for this picking
        try:
            substitution_report = delivery_report.get_substitution_report(self.ids)
        except Exception:
            # If substitution check fails, fall back to native behavior
            substitution_report = False

        if substitution_report:
            # Render the substitute report directly
            report_data = substitution_report._render(substitution_report.report_name, self.ids)
            # report_data is a tuple (pdf_content, format)
            filename = "%s_signed_delivery_slip" % self.name

            if self.partner_id:
                message = _("Order signed by %s", self.partner_id.name)
            else:
                message = _("Order signed")

            # Attach the report to the picking
            file_extension = report_data[1] if len(report_data) > 1 and report_data[1] else "pdf"
            self.message_post(
                attachments=[("%s.%s" % (filename, file_extension), report_data[0])],
                body=message,
            )
            return True
        return super()._attach_sign()
