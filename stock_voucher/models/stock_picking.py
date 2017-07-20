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
    vouchers = fields.Char(
        compute='_compute_vouchers'
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
    voucher_required = fields.Boolean(
        related='picking_type_id.voucher_required',
        readonly=True,
    )

    @api.multi
    @api.depends('voucher_ids.display_name')
    def _compute_vouchers(self):
        for rec in self:
            rec.vouchers = ', '.join(rec.mapped('voucher_ids.display_name'))

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

    @api.multi
    @api.onchange(
        'pack_operation_ids',
        'pack_operation_product_ids',
        'pack_operation_pack_ids',
    )
    def product_onchange(self):
        # self.declared_value = 0
        for rec in self:
            if not rec.automatic_declare_value:
                return False
            done_value = 0.0
            picking_value = 0.0
            inmediate_transfer = True
            for x in rec.pack_operation_ids:
                order_line = rec.env['sale.order.line'].search(
                    [('order_id', '=', rec.sale_id.id),
                     ('product_id', '=', x.product_id.id)], limit=1)
                if x.qty_done:
                    inmediate_transfer = False
                if order_line:
                    picking_value += (order_line.price_reduce * x.product_qty)
                    done_value += (order_line.price_reduce * x.qty_done)
                elif rec.picking_type_id.pricelist_id:
                    price = rec.picking_type_id.pricelist_id.with_context(
                        uom=x.product_id.uom_id.id).price_get(
                        x.product_id.id, x.qty_done or 1.0,
                        partner=rec.partner_id.id)[
                        rec.picking_type_id.pricelist_id.id]
                    picking_value += (price * x.product_qty)
                    done_value += (price * x.qty_done)

            if inmediate_transfer:
                rec.declared_value = picking_value
            else:
                rec.declared_value = done_value

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
        for page in range(estimated_number_of_pages):
            name = book.sequence_id.next_by_id()
            self.env['stock.picking.voucher'].create({
                'name': name,
                'book_id': book.id,
                'picking_id': self.id,
            })
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
    def do_stock_voucher_transfer_check(self):
        """
        Los separamos para usarlo en otros modulos
        """
        for picking in self:

            if picking.picking_type_id.code == 'outgoing':
                if (
                        picking.restrict_number_package and
                        not picking.number_of_packages > 0):
                    raise UserError(_('The number of packages can not be 0'))
            if picking.book_required and not picking.book_id:
                raise UserError(_('You must select a Voucher Book'))
            elif not picking.location_id.usage == 'customer' and \
                    picking.voucher_required and not picking.voucher_ids:
                raise UserError(_('You must set stock voucher numbers'))
        return True

    @api.multi
    def do_new_transfer(self):
        """
        We make checks before calling transfer
        """
        # we send picking_id on context so it can be used on wizards because
        # active_id could not be the picking
        self = self.with_context(picking_id=self.id)

        # estos chequeos no son tan grosos y preferimos hacerlos aca antes
        # de llamar al transfer porque demora mucho
        self.do_stock_voucher_transfer_check()

        res = super(StockPicking, self).do_new_transfer()
        # res none when no wizard  opended
        if res is None and len(self) == 1 and self.book_required:
            return self.do_print_voucher()
        return res


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    pricelist_id = fields.Many2one(
        'product.pricelist',
        'Pricelist',
        help='If you choose a pricelist, "Automatic Declare Value" is'
        ' enable on company and not sale order is found linked to the'
        ' picking, we will suggest declared value using this pricelist')
