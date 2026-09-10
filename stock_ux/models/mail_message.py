##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models
from odoo.tools.mail import html_to_inner_content


class MailMessage(models.Model):
    _inherit = "mail.message"

    tracking_summary = fields.Char(
        "Change",
        compute="_compute_tracking_summary",
        help="Readable summary of the message: its tracked field changes, or its body when it has none.",
    )

    def _compute_tracking_summary(self):
        # tracked field changes are rendered into the body since 20.0
        for message in self:
            message.tracking_summary = html_to_inner_content(message.body or "")
