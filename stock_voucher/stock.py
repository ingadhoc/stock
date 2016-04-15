# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models, _, api
import openerp.addons.decimal_precision as dp


class stock_picking_type(models.Model):
    _inherit = "stock.picking.type"

    book_required = fields.Boolean(
        string='Book Required?',
        help='If true, then a book will be requested on transfers of this '
        'type and a will automatically print the stock voucher.',
        )
    book_id = fields.Many2one(
        'stock.book', 'Book',
        help='Book suggested for pickings of this type',
        )
    # constraint de que el book y el type deben ser de la misma company_id


class stock_book(models.Model):
    _name = 'stock.book'
    _description = 'Stock Voucher Book'

    name = fields.Char(
        'Name', required=True,
    )
    sequence_id = fields.Many2one(
        'ir.sequence', 'Stock Voucher Sequence',
        domain=[('code', '=', 'stock.voucher')],
        context="{'default_code': 'stock.voucher', 'default_name': name, 'default_prefix': '000X-', 'default_padding': 8}",
        required=True,
    )
    lines_per_voucher = fields.Integer(
        'Lines Per Voucher', required=True,
        help="If voucher don't have a limit, then live 0. If not, this number will be used to calculate how many sequence are used on each picking"
    )
    # block_estimated_number_of_pages = fields.Boolean(
    #     'Block Estimated Number of Pages?',
    #     )
    company_id = fields.Many2one(
        'res.company', 'Company', required=True,
        default=lambda self: self.env[
            'res.company']._company_default_get('stock.book'),
    )


class stock_picking_voucher(models.Model):
    _name = 'stock.picking.voucher'
    _description = 'Stock Voucher Book'
    _rec_name = 'number'

    number = fields.Char(
        'Number', copy=False, required=True,
    )
    book_id = fields.Many2one(
        'stock.book', 'Voucher Book',
    )
    picking_id = fields.Many2one(
        'stock.picking', 'Picking', ondelete='cascade', required=True,
    )
    company_id = fields.Many2one(
        'res.company', 'Company',
        related='picking_id.company_id', readonly=True
    )
    # constraint de que el book y el picking deben ser de la misma company

    _sql_constraints = [
        ('voucher_number_uniq', 'unique(number, book_id)',
            _('The field "Number" must be unique per book.'))]


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
            number = self.env['ir.sequence'].next_by_id(
                book.sequence_id.id,)
            voucher_ids.append(self.env['stock.picking.voucher'].create({
                'number': number,
                'book_id': book.id,
                'picking_id': self.id,
            }).id)
        self.write({
            'book_id': book.id})
