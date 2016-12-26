# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, api, models
from math import ceil


class stock_print_stock_voucher(models.TransientModel):
    _name = 'stock.print_stock_voucher'
    _description = "Print Stock Voucher"

    @api.model
    def _get_picking(self):
        # if we came, for eg, from a sale order, active_id would be the
        # sale order id
        # self._context.get('active_id'))
        picking_id = self._context.get(
            'picking_id', self._context.get('active_id', False))
        # active_id = self._context.get('active_id', False)
        return self.env['stock.picking'].browse(picking_id)

    @api.model
    def _get_book(self):
        picking = self._get_picking()
        return picking.book_id

    picking_id = fields.Many2one(
        'stock.picking',
        default=_get_picking,
        required=True,
    )
    printed = fields.Boolean(
        compute='_get_printed',
    )
    book_id = fields.Many2one(
        'stock.book', 'Book', default=_get_book,
    )
    next_voucher_number = fields.Integer(
        'Next Voucher Number',
        related='book_id.sequence_id.number_next_actual', readonly=True,
    )
    estimated_number_of_pages = fields.Integer(
        'Number of Pages',
    )
    lines_per_voucher = fields.Integer(
        'Lines Per Voucher',
        related='book_id.lines_per_voucher',
        readonly=True,
    )

    @api.depends('picking_id', 'picking_id.voucher_ids')
    def _get_printed(self):
        printed = False
        if self.picking_id.voucher_ids:
            printed = True
        self.printed = printed

    @api.onchange('book_id', 'picking_id')
    def get_estimated_number_of_pages(self):
        lines_per_voucher = self.lines_per_voucher
        if lines_per_voucher == 0:
            estimated_number_of_pages = 1
        else:
            operations = len(self.picking_id.pack_operation_ids)
            estimated_number_of_pages = ceil(
                float(operations) / float(lines_per_voucher)
            )
        self.estimated_number_of_pages = estimated_number_of_pages

    @api.multi
    def do_print_voucher(self):
        return self.picking_id.do_print_voucher()

    @api.one
    def assign_numbers(self):
        self.picking_id.assign_numbers(
            self.estimated_number_of_pages, self.book_id)

    @api.multi
    def do_print_and_assign(self):
        self.assign_numbers()
        return self.do_print_voucher()

    @api.multi
    def do_clean(self):
        self.picking_id.voucher_ids.unlink()
        self.picking_id.book_id = False
