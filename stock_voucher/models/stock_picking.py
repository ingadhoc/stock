# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models, api, _
from openerp.exceptions import UserError
from math import ceil
import openerp.addons.decimal_precision as dp


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    book_id = fields.Many2one(
        'stock.book',
        'Voucher Book',
        copy=False,
    )
    voucher_ids = fields.One2many(
        'stock.picking.voucher',
        'picking_id',
        'Vouchers',
        copy=False
    )
    declared_value = fields.Float(
        'Declared Value',
        digits=dp.get_precision('Account'),
    )
    observations = fields.Text(
        'Observations'
    )
    restrict_number_package = fields.Boolean(
        related='company_id.restrict_number_package',
        readonly=True,
    )
    automatic_declare_value = fields.Boolean(
        related='company_id.automatic_declare_value',
        readonly=True,
    )
    book_required = fields.Boolean(
        related='picking_type_id.book_required',
        readonly=True,
    )

    @api.multi
    def get_estimated_number_of_pages(self):
        self.ensure_one()
        lines_per_voucher = self.book_id.lines_per_voucher
        if lines_per_voucher == 0:
            estimated_number_of_pages = 1
        else:
            operations = len(self.pack_operation_ids)
            estimated_number_of_pages = int(ceil(
                float(operations) / float(lines_per_voucher)
            ))
        return estimated_number_of_pages

    @api.one
    @api.constrains('picking_type_id')
    @api.onchange('picking_type_id')
    def _get_book(self):
        self.book_id = self.picking_type_id.book_id

    @api.one
    @api.constrains(
        'pack_operation_ids',
        'pack_operation_product_ids',
        'pack_operation_pack_ids',
    )
    @api.onchange(
        'pack_operation_ids',
        'pack_operation_product_ids',
        'pack_operation_pack_ids',
    )
    def product_onchange(self):
        # self.declared_value = 0
        if not self.automatic_declare_value:
            return True
        declared_value = 0.0
        for x in self.pack_operation_ids:
            order_line = self.env['sale.order.line'].search(
                [('order_id', '=', self.sale_id.id),
                 ('product_id', '=', x.product_id.id)], limit=1)
            declared_value += (order_line.price_reduce * x.qty_done)
        self.declared_value = declared_value

    @api.multi
    def do_print_voucher(self):
        '''This function prints the voucher'''
        report = self.env['report'].get_action(self, 'stock_voucher.report')
        # funcionalidad depreciada
        # if self._context.get('keep_wizard_open', False):
        #     report['type'] = 'ir.actions.report_dont_close_xml'
        return report

    @api.one
    def assign_numbers(self, estimated_number_of_pages, book):
        voucher_ids = []
        for page in range(estimated_number_of_pages):
            number = book.sequence_id.next_by_id()
            voucher_ids.append(self.env['stock.picking.voucher'].create({
                'number': number,
                'book_id': book.id,
                'picking_id': self.id,
            }).id)
        self.write({
            'book_id': book.id})

    @api.multi
    def do_transfer(self):
        """
        If book required then we assign numbers
        """
        res = super(StockPicking, self).do_transfer()
        for picking in self:
            if picking.book_required:
                picking.assign_numbers(
                    picking.get_estimated_number_of_pages(), picking.book_id)
        return res

    @api.multi
    def do_new_transfer(self):
        """
        We make checks before calling transfer
        """
        # we send picking_id on context so it can be used on wizards because
        # active_id could not be the picking
        self = self.with_context(picking_id=self.id)
        for picking in self:
            if picking.picking_type_id.code == 'outgoing':
                if (
                        picking.restrict_number_package and
                        not picking.number_of_packages > 0):
                    raise UserError(_('The number of packages can not be 0'))
            if picking.book_required and not picking.book_id:
                raise UserError(_('You must select a Voucher Book'))
        res = super(StockPicking, self).do_new_transfer()
        # res none when no wizard  opended
        if res is None and len(self) == 1 and self.book_required:
            return picking.do_print_voucher()
        return res
