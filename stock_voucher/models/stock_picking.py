# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models, api
import openerp.addons.decimal_precision as dp


class stock_picking(models.Model):
    _inherit = 'stock.picking'

    book_id = fields.Many2one(
        'stock.book', 'Voucher Book', copy=False, readonly=True,
    )
    voucher_ids = fields.One2many(
        'stock.picking.voucher', 'picking_id', 'Vouchers',
        copy=False
    )
    declared_value = fields.Float(
        'Declared Value', digits=dp.get_precision('Account'),
    )
    observations = fields.Text('Observations')

    @api.multi
    def do_print_voucher(self):
        '''This function prints the voucher'''
        report = self.env['report'].get_action(self, 'stock_voucher.report')
        if self._context.get('keep_wizard_open', False):
            report['type'] = 'ir.actions.report_dont_close_xml'
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
