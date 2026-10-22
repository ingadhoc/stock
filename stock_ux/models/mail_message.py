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
        # field tracking messages are stored with an empty body: the change lives in
        # tracking_value_ids, so a list showing only the body renders them blank
        for message in self:
            changes = [
                "%s: %s → %s" % (tracking["fieldInfo"]["changedField"], tracking["oldValue"], tracking["newValue"])
                for tracking in message.sudo().tracking_value_ids._tracking_value_format()
            ]
            message.tracking_summary = " | ".join(changes) or html_to_inner_content(message.body or "")
