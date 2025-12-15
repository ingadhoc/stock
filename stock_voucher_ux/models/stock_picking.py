##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    printed = fields.Boolean()

    with_vouchers = fields.Boolean(
        compute="_compute_with_vouchers",
    )

    next_voucher_number = fields.Integer(
        "Next Voucher Number",
        related="book_id.sequence_id.number_next_actual",
    )

    autoprinted = fields.Boolean(
        related="book_id.autoprinted",
    )

    @api.depends("voucher_ids")
    def _compute_with_vouchers(self):
        for rec in self:
            rec.with_vouchers = bool(self.voucher_ids)

    def do_print_voucher(self):
        self.printed = True
        if self.book_id:
            self.book_id = self.book_id.id
        return super(StockPicking, self).do_print_voucher()

    def do_print_and_assign(self):
        if not self.book_id and self.picking_type_code != "incoming":
            raise UserError("Primero debe seleccionar un talonario")
        if self.autoprinted == False:
            self.printed = True
            return self.with_context(assign=True).do_print_voucher()
        else:
            if self.book_id.sequence_to and int(self.next_voucher_number) > int(self.book_id.sequence_to):
                raise UserError(
                    self.env._(
                        "The voucher number %s exceeds the range specified in the CAI. Please update the range or use a different CAI with a different range.",
                        self.next_voucher_number,
                    )
                )
            self.assign_numbers(1, self.book_id)
            return self.do_print_voucher()

    def clean_voucher_data(self):
        return super(StockPicking, self).clean_voucher_data()
