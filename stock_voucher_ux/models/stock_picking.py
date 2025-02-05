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

    book_id = fields.Many2one(
        "stock.book",
        "Book",
        default=lambda self: self._get_book(),
    )

    next_voucher_number = fields.Integer(
        "Next Voucher Number",
        related="book_id.sequence_id.number_next_actual",
    )

    autoprinted = fields.Boolean(
        related="book_id.autoprinted",
    )

    @api.model
    def _get_book(self):
        return self.book_id or self.env["stock.book"].search([("company_id", "=", self.company_id.id)], limit=1)

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
            self.assign_numbers(1, self.book_id)
            return self.do_print_voucher()

    def clean_voucher_data(self):
        return super(StockPicking, self).clean_voucher_data()
