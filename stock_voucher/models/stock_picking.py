##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api, _
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    book_id = fields.Many2one(
        'stock.book',
        'Voucher Book',
        copy=False,
    )
    vouchers = fields.Char(
        compute='_compute_vouchers',
    )
    voucher_ids = fields.One2many(
        'stock.picking.voucher',
        'picking_id',
        'Vouchers',
        copy=False,
    )
    declared_value = fields.Float(
        digits=dp.get_precision('Account'),
    )
    observations = fields.Text(
    )
    restrict_number_package = fields.Boolean(
        related='picking_type_id.restrict_number_package',
        readonly=True,
    )
    automatic_declare_value = fields.Boolean(
        related='picking_type_id.automatic_declare_value',
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
    next_number = fields.Integer(
        related='book_id.next_number',
        readonly=True,
    )

    @api.depends('voucher_ids.display_name')
    def _compute_vouchers(self):
        for rec in self:
            rec.update({
                'vouchers': ', '.join(rec.mapped('voucher_ids.display_name'))
            })

    def get_estimated_number_of_pages(self):
        self.ensure_one()
        res = 1
        lines_per_voucher = self.book_id.lines_per_voucher
        if lines_per_voucher == 0:
            return res

        operations = len(self.move_lines)
        res = int(-(-float(operations) // float(lines_per_voucher)))
        return res

    @api.constrains('picking_type_id')
    @api.onchange('picking_type_id')
    def _get_book(self):
        for rec in self:
            rec.update({'book_id': rec.picking_type_id.book_id.id})

    @api.constrains('move_lines')
    @api.onchange('move_lines')
    def product_onchange(self):
        # self.declared_value = 0
        SaleOrderLine = self.env['sale.order.line']
        for rec in self.filtered(lambda x: x.automatic_declare_value):
            done_value = 0.0
            picking_value = 0.0
            inmediate_transfer = True
            pricelist = False
            for move_line in rec.move_lines:
                order_line = SaleOrderLine.search(
                    [('order_id', '=', rec.sale_id.id),
                     ('product_id', '=', move_line.product_id.id)], limit=1)
                if move_line.quantity_done:
                    inmediate_transfer = False
                if order_line:
                    pricelist = rec.sale_id.pricelist_id
                    # convert quantities to uom of the sale order
                    so_product_qty = move_line.product_id.uom_id.\
                        _compute_quantity(
                            move_line.ordered_qty, order_line.product_uom)
                    so_qty_done = move_line.product_id.uom_id.\
                        _compute_quantity(
                            move_line.quantity_done, order_line.product_uom)
                    picking_value += (order_line.price_reduce * so_product_qty)
                    done_value += (order_line.price_reduce * so_qty_done)
                elif rec.picking_type_id.pricelist_id:
                    pricelist = rec.picking_type_id.pricelist_id
                    price = rec.picking_type_id.pricelist_id.with_context(
                        uom=move_line.product_id.uom_id.id).price_get(
                        move_line.product_id.id,
                        move_line.quantity_done or 1.0,
                        partner=rec.partner_id.id)[
                        rec.picking_type_id.pricelist_id.id]
                    picking_value += (price * move_line.ordered_qty)
                    done_value += (price * move_line.quantity_done)

            declared_value = picking_value if inmediate_transfer\
                else done_value
            if pricelist:
                # we convert the declared_value to the currency of the company
                rec.declared_value = pricelist.currency_id.compute(
                    declared_value, rec.company_id.currency_id)
            else:
                rec.declared_value = declared_value

    @api.multi
    def do_print_voucher(self):
        '''This function prints the voucher'''
        report = self.env['ir.actions.report'].search(
            [('report_name', '=', 'stock.report_picking')],
            limit=1).report_action(self)
        return report

    @api.multi
    def assign_numbers(self, estimated_number_of_pages, book):
        self.ensure_one()
        StockPickingVoucher = self.env['stock.picking.voucher']
        for page in range(estimated_number_of_pages):
            name = book.sequence_id.next_by_id()
            StockPickingVoucher.create({
                'name': name,
                'book_id': book.id,
                'picking_id': self.id,
            })
        self.message_post(body=_(
            'Números de remitos asignados: %s') % (self.vouchers))
        self.write({
            'book_id': book.id})

    @api.multi
    def clean_voucher_data(self):
        self.voucher_ids.unlink()
        self.book_id = False
        self.message_post(_('The assigned voucher were deleted'))

    @api.multi
    def action_done(self):
        """
        If book required then we assign numbers
        """
        res = super(StockPicking, self).action_done()
        if self._context.get('do_not_assign_numbers', False):
            return res
        for picking in self.filtered('book_required'):
            picking.assign_numbers(
                picking.get_estimated_number_of_pages(),
                picking.book_id)
        return res

    @api.multi
    def do_stock_voucher_transfer_check(self):
        """
        We separe to use it in other modules
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
    def button_validate(self):
        """
        We make checks before calling transfer
        """
        # we send picking_id on context so it can be used on wizards because
        # active_id could not be the picking
        self = self.with_context(picking_id=self.id)
        self.do_stock_voucher_transfer_check()

        res = super(StockPicking, self).button_validate()
        # res none when no wizard opended
        if res is None and len(self) == 1 and self.book_required:
            return self.do_print_voucher()
        return res
