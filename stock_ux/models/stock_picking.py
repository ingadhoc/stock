# flake8: noqa
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools.float_utils import float_compare


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
                % (
                    ",".join(not_del_pickings.mapped("picking_type_id.name")),
                    not_del_pickings.ids,
                )
            )
        return super().unlink()

    def copy(self, default=None):
        for picking in self:
            if not default and picking.picking_type_id.block_additional_quantity:
                raise UserError(
                    _(
                        'You can not duplicate a Picking because "Block Additional Quantity" is enabled on the picking type "%(name)s"'
                    )
                    % {"name": picking.picking_type_id.name}
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
            # If stock_voucher is installed, skip email sending when validating the picking
            if "book_required" in rec._fields and not rec._context.get("from_assign_numbers"):
                continue

            if rec.picking_type_id.mail_template_id:
                try:
                    rec.with_context(
                        email_notification_force_header=True,
                        email_notification_force_footer=True,
                    ).message_post_with_source(rec.picking_type_id.mail_template_id)
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

    def _sanity_check(self, separate_pickings=True):
        res = super()._sanity_check(separate_pickings=separate_pickings)
        self._check_serial_quantity_consistency()
        return res

    def _check_serial_quantity_consistency(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        broken = []
        for picking in self:
            moves = picking.move_ids.filtered(
                lambda m: m.state not in ('done', 'cancel')
                and m.picked
                and m.product_id.tracking == 'serial')
            for move in moves:
                serial_count = len(move.move_line_ids.filtered(
                    lambda ml: ml.picked and ml.lot_id
                    and float_compare(ml.quantity, 0, precision_digits=precision) != 0))
                if float_compare(abs(move.quantity), serial_count, precision_digits=precision) != 0:
                    broken.append((move, serial_count))
        if broken:
            raise UserError(_(
                "You can not validate this transfer: the following serial tracked products "
                "have a done quantity different from the number of assigned serial numbers. "
                "Please assign the missing serials or adjust the quantity:\n%s") % (
                "\n".join(
                    _("- %s: done quantity %s, assigned serials %s") % (
                        move.product_id.display_name, move.quantity, serial_count)
                    for move, serial_count in broken)))

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
<<<<<<< 5c4c4f22e4695c1a7871d31b873b66b0e893cf18
            return {
                "warning": {
                    "title": "High Number of Packages",
                    "message": "Be careful about the number of packages you are trying to insert. "
                    "It may cause an error when trying to render the 'Shipping Label' template",
                }
            }

    def write(self, vals):
        """
        Overrides the default write method to restrict changing the 'picking_type_id' field
        for users belonging to the 'group_restrict_edit_picking_type' group. If a user in this
        group attempts to modify the 'picking_type_id' of a picking that already has a value set,
        a UserError is raised to prevent the operation. Otherwise, proceeds with the standard
        write operation.

        :param vals: Dictionary of field values to update.
        :raises UserError: If a restricted user tries to change the 'picking_type_id' after it has been set.
        :return: Result of the superclass write method.
        """

        if "picking_type_id" in vals:
            user = self.env.user
            if user.has_group("stock_ux.group_restrict_edit_picking_type"):
                for picking in self:
                    if picking.picking_type_id:
                        raise UserError(
                            _(
                                "You cannot change the Operation Type once it has been set. "
                                "This action is restricted for your user. "
                                "Please contact your Inventory Manager if you need to perform this operation."
                            )
                        )
        return super().write(vals)

    def button_validate(self):
        """Valida que no se transfiera más de la demanda inicial."""
        for picking in self:
            if picking.picking_type_id.block_additional_quantity:
                precision = self.env["decimal.precision"].precision_get("Product Unit of Measure")
                for move in picking.move_ids.filtered(lambda m: m.state not in ("draft", "cancel")):
                    if float_compare(move.quantity, move.product_uom_qty, precision_digits=precision) == 1:
                        raise UserError(
                            _(
                                "Cannot transfer more than initial demand!\n\n"
                                "Product: %(product)s\n"
                                "Initial Demand: %(demand)s\n"
                                "Attempted Transfer: %(quantity)s\n\n"
                                "Please update the source document (Purchase/Sales Order) to increase quantities.",
                                product=move.product_id.display_name,
                                demand=move.product_uom_qty,
                                quantity=move.quantity,
                            )
                        )
        return super().button_validate()
||||||| 0b86a64b7e1a4ff860ae521461ed182c091c0d60
            return {
                "warning": {
                    "title": "High Number of Packages",
                    "message": "Be careful about the number of packages you are trying to insert. "
                    "It may cause an error when trying to render the 'Shipping Label' template",
                }
            }
=======
            raise UserError(
                _("Be careful about the number of packages you are trying to insert. "
                  "It may cause an error when trying to render the 'Shipping Label' template")
            )
>>>>>>> a4c1ff62ff5d01080e27d80ead9fc268afd8a548
