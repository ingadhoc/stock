# flake8: noqa
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    block_manual_lines = fields.Boolean(
        related="picking_type_id.block_manual_lines",
    )
    observations = fields.Html()

    # Agregamos para poder modificar dominio del boton button_validate
    operation_type_additional_quantities = fields.Boolean(related="picking_type_id.block_additional_quantity")

    number_of_packages = fields.Integer(
        string="Number of Packages",
        copy=False,
    )

    def unlink(self):
        """
        To avoid errors we block deletion of pickings in other state than
        draft or cancel
        """
        not_del_pickings = self.filtered(
            lambda x: x.picking_type_id.block_picking_deletion or x.state not in ("draft", "cancel")
        )
        if not_del_pickings:
            raise ValidationError(
                _(
                    'You can not delete this pickings because "Block picking '
                    'deletion" is enable on the picking type/s "%s" '
                    "or the state of the picking is not draft or cancel.\n"
                    "Picking Ids: %s"
                )
                % (",".join(not_del_pickings.mapped("picking_type_id.name")), not_del_pickings.ids)
            )
        return super().unlink()

    def copy(self, default=None):
        for picking in self:
            if not default and picking.picking_type_id.block_additional_quantity:
                raise UserError(
                    _(
                        'You can not duplicate a Picking because "Block'
                        ' Additional Quantity" is enabled on the picking type "%s"'
                    )
                    % (picking.picking_type_id.name)
                )
        return super().copy(default=default)

    @api.onchange("location_id")
    def change_location(self):
        # we only change moves locations if picking in draft
        if self.state == "draft":
            self.move_ids.update({"location_id": self.location_id.id})

    @api.onchange("location_dest_id")
    def change_location_dest(self):
        # we only change moves locations if picking in draft
        if self.state == "draft":
            self.move_ids.update({"location_dest_id": self.location_dest_id.id})

    def _send_confirmation_email(self):
        for rec in self:
            if rec.picking_type_id.mail_template_id:
                try:
                    rec.message_post_with_source(rec.picking_type_id.mail_template_id)
                except Exception as error:
                    title = _("ERROR: Picking was not sent via email")
                    rec.message_post(
                        body="<br/><br/>".join(
                            [
                                "<b>" + title + "</b>",
                                _("Please check the email template associated with the picking type."),
                                "<code>" + str(error) + "</code>",
                            ]
                        ),
                        body_is_html=True,
                    )
            else:
                super(StockPicking, self)._send_confirmation_email()

    def _action_done(self):
        for rec in self.with_context(mail_notify_force_send=False).filtered("picking_type_id.mail_template_id"):
            try:
                rec.message_post_with_template(rec.picking_type_id.mail_template_id.id)
            except Exception as error:
                title = _("ERROR: Picking was not sent via email")
                rec.message_post(
                    body="<br/><br/>".join(
                        [
                            "<b>" + title + "</b>",
                            _("Please check the email template associated with" " the picking type."),
                            "<code>" + str(error) + "</code>",
                        ]
                    ),
                )
        return super()._action_done()

    def new_force_availability(self):
        self.action_assign()
        for rec in self.mapped("move_ids").filtered(lambda m: m.state not in ["cancel", "done"]):
            # this two could go together but we keep similar to odoo sm._quantity_done_set
            if not rec.move_line_ids:
                rec.quantity = rec.product_uom_qty
            elif len(rec.move_line_ids) == 1:
                rec.quantity = rec.product_uom_qty
            else:
                for line in rec.move_line_ids:
                    line.quantity = line.quantity_product_uom

    def _put_in_pack(self, move_line_ids):
        # we send to skip a process of check qty when is sending through the copy method.
        return super()._put_in_pack(move_line_ids.with_context(put_in_pack=True))

    @api.onchange("number_of_packages")
    def _check_number_of_packages(self):
        """
        To avoid errors when trying to render a template with a large number of packages
        """
        if self.number_of_packages > 100:
            return {
                "warning": {
                    "title": "High Number of Packages",
                    "message": "Be careful about the number of packages you are trying to insert. "
                    "It may cause an error when trying to render the 'Shipping Label' template",
                }
            }
