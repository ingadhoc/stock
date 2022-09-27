##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    number_of_packages = fields.Integer(
        string='Number of Packages',
        copy=False,
    )
    book_id = fields.Many2one(
        'stock.book',
        'Voucher Book',
        copy=False,
        ondelete='restrict',
    )
    vouchers = fields.Char(
        compute='_compute_vouchers',
        string='Vouchers (string)',
        store=True,
    )
    voucher_ids = fields.One2many(
        'stock.picking.voucher',
        'picking_id',
        'Vouchers',
        copy=False,
    )
    declared_value = fields.Float(
        digits='Account',
        compute='_compute_declared_value',
        store=True,
        readonly=False,
    )
    automatic_declare_value = fields.Boolean(
        related='picking_type_id.automatic_declare_value',
    )
    book_required = fields.Boolean(
        related='picking_type_id.book_required',
    )
    voucher_required = fields.Boolean(
        related='picking_type_id.voucher_required',
    )
    next_number = fields.Integer(
        related='book_id.next_number',
    )

    @api.depends('voucher_ids.display_name')
    def _compute_vouchers(self):
        for rec in self:
            rec.vouchers = ', '.join(rec.mapped('voucher_ids.display_name'))

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
        for rec in self.filtered(lambda x: x.picking_type_id.book_id):
            rec.book_id = rec.picking_type_id.book_id.id

    def do_print_voucher(self):
        '''This function prints the voucher'''
        return self.env.ref('stock.action_report_delivery').report_action(self)

    def assign_numbers(self, estimated_number_of_pages, book):
        self.ensure_one()
        list_of_vouchers = []
        for page in range(estimated_number_of_pages):
            list_of_vouchers.append({
                'name': book.sequence_id.next_by_id(),
                'book_id': book.id,
                'picking_id': self.id,
            })
        self.env['stock.picking.voucher'].create(list_of_vouchers)
        self.message_post(body=_(
            'Números de remitos asignados: %s') % (self.vouchers))
        self.write({'book_id': book.id})

    def clean_voucher_data(self):
        self.voucher_ids.unlink()
        self.book_id = False
        self.message_post(body=_('The assigned voucher were deleted'))

    def _action_done(self):
        """
        If book required then we assign numbers
        """
        res = super()._action_done()
        if self._context.get('do_not_assign_numbers', False):
            return res
        for picking in self.filtered('book_required'):
            picking.assign_numbers(
                picking.get_estimated_number_of_pages(),
                picking.book_id)
        return res

    def do_stock_voucher_transfer_check(self):
        """
        We separe to use it in other modules
        """
        for picking in self:

            if picking.picking_type_id.code == 'outgoing':
                if (
                        picking.picking_type_id.restrict_number_package and
                        not picking.number_of_packages > 0):
                    raise UserError(_('The number of packages can not be 0'))
            if picking.book_required and not picking.book_id:
                raise UserError(_('You must select a Voucher Book'))
            elif not picking.location_id.usage == 'customer' and \
                    picking.voucher_required and not picking.voucher_ids:
                raise UserError(_('You must set stock voucher numbers'))
        return True

    def button_validate(self):
        """
        We make checks before calling transfer
        """
        # we send picking_id on context so it can be used on wizards because
        # active_id could not be the picking
        self = self.with_context(picking_ids=self.ids)
        self.do_stock_voucher_transfer_check()

        res = super().button_validate()
        # res none when no wizard opended
        if res is None and len(self) == 1 and self.book_required:
            return self.do_print_voucher()
        return res

    @api.depends(
        'automatic_declare_value',
        'move_lines.state',
        'move_lines.quantity_done',
        )
    def _compute_declared_value(self):
        for rec in self.filtered(lambda p: p.automatic_declare_value and p.state not in ['done', 'cancel']):
            done_value = 0.0
            picking_value = 0.0
            inmediate_transfer = True
            pricelist = False
            stock_bom_lines = self.env['stock.move']
            for move_line in rec.move_lines.filtered(
                    lambda x: x.state != 'cancel'):
                order_line = move_line.sale_line_id
                if move_line.quantity_done:
                    inmediate_transfer = False
                if order_line:
                    pricelist = rec.sale_id.pricelist_id
                    # this should happends only if on SO it's a bom kit
                    if not order_line.product_id == move_line.product_id:
                        stock_bom_lines |= move_line
                        continue
                    so_product_qty = move_line.product_uom_qty
                    so_qty_done = move_line.quantity_done
                    # convert quantities if move line uom and sale line uom
                    # are different
                    if move_line.product_uom != order_line.product_uom:
                        so_product_qty = \
                            move_line.product_uom._compute_quantity(
                                move_line.product_uom_qty,
                                order_line.product_uom)
                        so_qty_done = \
                            move_line.product_uom._compute_quantity(
                                move_line.quantity_done,
                                order_line.product_uom)
                    picking_value += (order_line.price_reduce_taxexcl *
                                      so_product_qty)
                    done_value += (order_line.price_reduce_taxexcl *
                                   so_qty_done)
                elif rec.picking_type_id.pricelist_id:
                    pricelist = rec.picking_type_id.pricelist_id
                    price = rec.picking_type_id.pricelist_id.with_context(
                        uom=move_line.product_uom.id).price_get(
                        move_line.product_id.id,
                        move_line.quantity_done or 1.0,
                        partner=rec.partner_id.id)[
                        rec.picking_type_id.pricelist_id.id]
                    picking_value += (price * move_line.product_uom_qty)
                    done_value += (price * move_line.quantity_done)

            # This is for product in a kit (should only happen if sale_mrp ins
            # installed). If it is bom we only compute amount if all bom
            # components are deliverd (same as in bom _get_delivered_qty)
            bom_enable = 'bom_ids' in self.env['product.template']._fields
            if bom_enable:
                for so_bom_line in stock_bom_lines.mapped('sale_line_id'):
                    bom = self.env['mrp.bom']._bom_find(
                        product=so_bom_line.product_id,
                        company_id=so_bom_line.company_id.id)
                    if bom and bom.type == 'phantom':
                        bom_moves = so_bom_line.move_ids & stock_bom_lines
                        done_avg = []
                        picking_avg = []
                        boms, lines = bom.sudo().explode(
                            so_bom_line.product_id,
                            so_bom_line.product_uom_qty,
                            picking_type=bom.picking_type_id)
                        for move in bom_moves:
                            bom_quantity = 0.0
                            for bom_line, line_data in lines:
                                if bom_line.product_id == move.product_id:
                                    bom_quantity += line_data['qty']
                            if not bom_quantity:
                                continue
                            picking_avg.append((
                                move.product_uom_qty / bom_quantity))
                            done_avg.append((move.quantity_done / bom_quantity))
                        picking_value += so_bom_line.price_reduce_taxexcl * (
                            sum(picking_avg) / len(picking_avg))
                        done_value += so_bom_line.price_reduce_taxexcl * (
                            sum(done_avg) / len(done_avg))

            declared_value = picking_value if inmediate_transfer\
                else done_value
            if pricelist:
                # we convert the declared_value to the currency of the company
                rec.declared_value = pricelist.currency_id._convert(
                    declared_value, rec.company_id.currency_id, rec.company_id,
                    rec.sale_id.date_order or fields.Date.today())
            else:
                rec.declared_value = declared_value
