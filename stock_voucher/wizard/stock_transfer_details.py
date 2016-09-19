# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models, api, _
from openerp.exceptions import Warning
import openerp.addons.decimal_precision as dp
from math import ceil


class stock_transfer_details(models.TransientModel):
    _inherit = 'stock.transfer_details'

    book_required = fields.Boolean(
        related='picking_id.picking_type_id.book_required',
        readonly=True,
    )
    book_id = fields.Many2one(
        'stock.book',
        'Book',
    )
    number_of_packages = fields.Integer(
        string="Number of Packages",
    )
    declared_value = fields.Float(
        'Declared Value',
        digits=dp.get_precision('Account'),
        # default=_get_declared_value
    )
    # block_estimated_number_of_pages = fields.Boolean(
    #     related='book_id.block_estimated_number_of_pages',
    #     )
    next_voucher_number = fields.Integer(
        'Next Voucher Number',
        related='book_id.sequence_id.number_next_actual', readonly=True,
    )
    lines_per_voucher = fields.Integer(
        'Lines Per Voucher',
        related='book_id.lines_per_voucher',
        readonly=True,
    )
    automatic_declare_value = fields.Boolean(
        compute='_get_automatic_restrict'
    )
    restrict_number_package = fields.Boolean(
        compute='_get_automatic_restrict'
    )

    @api.one
    def _get_automatic_restrict(self):
        company = self.picking_id.company_id
        self.automatic_declare_value = company.automatic_declare_value
        self.restrict_number_package = company.restrict_number_package

    @api.multi
    def get_estimated_number_of_pages(self):
        self.ensure_one()
        lines_per_voucher = self.lines_per_voucher
        if lines_per_voucher == 0:
            estimated_number_of_pages = 1
        else:
            operations = len(self.picking_id.pack_operation_ids)
            estimated_number_of_pages = int(ceil(
                float(operations) / float(lines_per_voucher)
            ))
        return estimated_number_of_pages

    @api.multi
    def do_detailed_transfer(self):
        self.ensure_one()
        super(stock_transfer_details, self).do_detailed_transfer()
        if self.picking_id.picking_type_id.code == 'outgoing':
            if (
                    self.restrict_number_package and
                    not self.number_of_packages > 0):
                raise Warning(_('The number of packages can not be 0'))
        if self.book_required:
            self.picking_id.assign_numbers(
                self.get_estimated_number_of_pages(), self.book_id)
            self.picking_id.declared_value = self.declared_value
            self.picking_id.number_of_packages = self.number_of_packages
            return self.picking_id.do_print_voucher()
        return True

    @api.one
    @api.constrains('picking_id', 'item_ids')
    @api.onchange('picking_id', 'item_ids')
    def product_onchange(self):
        self.declared_value = 0
        picking = self.picking_id
        for x in self.item_ids:
            order_line = self.env['sale.order.line'].search(
                [('order_id', '=', picking.sale_id.id),
                 ('product_id', '=', x.product_id.id)], limit=1)
            self.declared_value = self.declared_value + \
                (order_line.price_reduce * x.quantity)

    @api.one
    @api.constrains('picking_id')
    @api.onchange('picking_id')
    def _get_book(self):
        self.book_id = self.picking_id.picking_type_id.book_id
        self.number_of_packages = self.picking_id.number_of_packages
