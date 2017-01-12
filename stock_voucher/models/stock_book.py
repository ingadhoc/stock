# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models, api, _
from openerp.exceptions import UserError


class stock_picking_type(models.Model):
    _inherit = "stock.picking.type"

    book_required = fields.Boolean(
        string='Book Required?',
        help='If true, then a book will be requested on transfers of this '
        'type and a will automatically print the stock voucher.',
    )
    voucher_required = fields.Boolean(
        string='Book Required?',
        help='If true, voucher numbers will be required before validation',
    )
    # only for incoming
    voucher_number_unique = fields.Boolean(
        string='Book Unique?',
        help='If true, voucher numbers will be required to be unique for same'
        ' partner',
    )
    voucher_number_validator_id = fields.Many2one(
        'base.validator',
        help='Choose a validation if you want to validate voucher numbers'
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
        context="{'default_code': 'stock.voucher', 'default_name': name, "
        "'default_prefix': '000X-', 'default_padding': 8, "
        "'default_implementation': 'no_gap',}",
        required=True,
    )
    lines_per_voucher = fields.Integer(
        'Lines Per Voucher', required=True,
        help="If voucher don't have a limit, then live 0. If not, this number "
        "will be used to calculate how many sequence are used on each picking"
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
    # _rec_name = 'number'

    # we keep this for report compatibility
    number = fields.Char(
        related='name',
    )
    # because m2m tags widget send only values to name field
    name = fields.Char(
        'Number', copy=False, required=True, oldname='number',
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
        ('voucher_number_uniq', 'unique(name, book_id)',
            _('The field "Number" must be unique per book.'))]

    @api.multi
    @api.constrains('name', 'picking_id')
    def check_voucher_number_unique(self):
        """
        Check internal pickings with voucher number unique
        """
        for rec in self:
            pick_type = rec.picking_id.picking_type_id
            if pick_type.code == 'incoming':
                name = pick_type.voucher_number_validator_id.validate_value(
                    rec.name)
                if name and name != rec.name:
                    rec.name = name
                if pick_type.voucher_number_unique:
                    same_number_recs = self.search([
                        ('picking_id.partner_id', '=',
                            rec.picking_id.partner_id.id),
                        ('name', '=', rec.name),
                        ('id', '!=', rec.id),
                    ])
                    if same_number_recs:
                        raise UserError(_(
                            'Picking voucher number must be unique per '
                            'partner'))
