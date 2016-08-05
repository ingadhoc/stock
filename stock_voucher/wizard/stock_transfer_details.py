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

    @api.model
    def _get_picking(self):
        context = self._context
        picking_ids = context.get('active_ids', [])
        active_model = context.get('active_model')
        # Partial Picking Processing may only be done for one picking at a time
        if not picking_ids or len(picking_ids) != 1:
            return self.env['stock.picking']
        assert active_model in ('stock.picking'), 'Bad context propagation'
        picking_id, = picking_ids
        return self.env['stock.picking'].browse(picking_id)

    @api.model
    def _get_book(self):
        picking = self._get_picking()
        return picking.picking_type_id.book_id

    @api.model
    def _get_declared_value(self):
        picking = self._get_picking()
        declared_value = 0
        for x in picking.move_lines:
            order_line = self.env['sale.order.line'].search(
                [('order_id', '=', picking.sale_id.id),
                 ('product_id', '=', x.product_id.id)], limit=1)
            declared_value = declared_value + \
                (order_line.price_reduce * x.product_uom_qty)
        return declared_value

    @api.model
    def _get_number_of_packages(self):
        picking = self._get_picking()
        return picking.number_of_packages

    book_required = fields.Boolean(
        related='picking_id.picking_type_id.book_required'
    )
    book_id = fields.Many2one(
        'stock.book',
        'Book',
        default=_get_book,
    )
    number_of_packages = fields.Integer(
        string="Number of Packages",
        default=_get_number_of_packages)
    declared_value = fields.Float(
        'Declared Value',
        digits=dp.get_precision('Account'),
        default=_get_declared_value
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
    )
    automatic_declare_value = fields.Boolean(
        compute='_get_automatic_restrict'
    )
    restrict_number_package = fields.Boolean(
        compute='_get_automatic_restrict'
    )

    @api.one
    def _get_automatic_restrict(self):
        self.automatic_declare_value = self.env['res.users'].browse(
            self._uid).company_id.automatic_declare_value
        self.restrict_number_package = self.env['res.users'].browse(
            self._uid).company_id.restrict_number_package

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
            if self.restrict_number_package and not self.number_of_packages > 0:
                raise Warning(_('The number of packages can not be 0'))
        if self.book_required:
            self.picking_id.assign_numbers(
                self.get_estimated_number_of_pages(), self.book_id)
            self.picking_id.declared_value = self.declared_value
            self.picking_id.number_of_packages = self.number_of_packages
            return self.picking_id.do_print_voucher()
        return True

    @api.one
    @api.onchange('item_ids')
    def product_onchange(self):
        self.declared_value = 0
        picking = self.picking_id or self._get_picking()
        for x in self.item_ids:
            order_line = self.env['sale.order.line'].search(
                [('order_id', '=', picking.sale_id.id),
                 ('product_id', '=', x.product_id.id)], limit=1)
            self.declared_value = self.declared_value + \
                (order_line.price_reduce * x.quantity)
