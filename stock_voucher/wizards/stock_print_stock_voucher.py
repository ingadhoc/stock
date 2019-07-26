##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, api, models


class StockPrintStockVoucher(models.TransientModel):
    _name = 'stock.print_stock_voucher'
    _description = "Print Stock Voucher"

    @api.model
    def _get_picking(self):
        # if we came, for eg, from a sale order, active_id would be the
        # sale order id
        # self._context.get('active_id'))
        picking_id = self._context.get(
            # 'picking_id', self._context.get('active_id', False))
            'picking_id')
        # active_id = self._context.get('active_id', False)
        return self.env['stock.picking'].browse(picking_id)

    @api.model
    def _get_book(self):
        picking = self._get_picking()
        return picking.book_id

    picking_id = fields.Many2one(
        'stock.picking',
        default=lambda self: self._get_picking(),
        required=True,
    )
    printed = fields.Boolean(
    )
    with_vouchers = fields.Boolean(
        compute='_compute_with_vouchers',
    )
    book_id = fields.Many2one(
        'stock.book',
        'Book',
        default=lambda self: self._get_book(),
    )
    next_voucher_number = fields.Integer(
        'Next Voucher Number',
        related='book_id.sequence_id.number_next_actual',
    )
    estimated_number_of_pages = fields.Integer(
        'Number of Pages',
    )
    lines_per_voucher = fields.Integer(
        'Lines Per Voucher',
        related='book_id.lines_per_voucher',
    )

    @api.depends('picking_id', 'picking_id.voucher_ids')
    def _compute_with_vouchers(self):
        for rec in self:
            rec.with_vouchers = bool(rec.picking_id.voucher_ids)

    @api.onchange('book_id', 'picking_id')
    def get_estimated_number_of_pages(self):
        lines_per_voucher = self.lines_per_voucher
        if lines_per_voucher == 0:
            self.estimated_number_of_pages = 1
            return

        operations = len(self.picking_id.move_line_ids)
        estimated_number_of_pages = int(
            -(-float(operations) // float(lines_per_voucher)))
        self.estimated_number_of_pages = estimated_number_of_pages

    @api.multi
    def do_print_voucher(self):
        self.printed = True
        return self.picking_id.do_print_voucher()

    @api.multi
    def assign_numbers(self):
        self.picking_id.assign_numbers(
            self.estimated_number_of_pages, self.book_id)

    @api.multi
    def do_print_and_assign(self):
        self.assign_numbers()
        return {
            'actions': [
                {'type': 'ir.actions.act_window_close'},
                self.do_print_voucher(),
            ],
            'type': 'ir.actions.act_multi',
        }

    @api.multi
    def do_clean(self):
        self.picking_id.clean_voucher_data()
