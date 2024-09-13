##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, api, models, _


class StockPrintStockVoucher(models.TransientModel):
    _name = 'stock.print_batch_stock_voucher'
    _description = "Print batch Stock Voucher"

   
    @api.model
    def _get_pickings(self):
        # if we came, for eg, from a sale order, active_id would be the
        # self._context.get('active_id'))
        picking_ids = self.env[self._context.get('active_model')].browse(int(self._context.get('active_id'))).picking_ids
        return picking_ids

    @api.model
    def _get_book(self):
        picking = self._get_pickings()
        return picking.book_id or self.env['stock.book'].search([('company_id', '=', picking.company_id.id)], limit=1)

    picking_ids = fields.Many2many(
        'stock.picking',
        default= lambda self: self._get_pickings(),
        required=True,
    )
    
    printed = fields.Boolean(
    )
    with_vouchers = fields.Boolean(
        compute='_compute_with_vouchers',
    )
    book_id = fields.Many2one(
        'stock.book',
        'Book',
        default=lambda self: self._get_book(),
    )
    next_voucher_number = fields.Integer(
        'Next Voucher Number',
        related='book_id.sequence_id.number_next_actual',
    )
    estimated_number_of_pages = fields.Integer(
        'Number of Pages',
    )
    lines_per_voucher = fields.Integer(
        'Lines Per Voucher',
        related='book_id.lines_per_voucher',
    )

    @api.depends('picking_ids', 'picking_ids.voucher_ids')
    def _compute_with_vouchers(self):
        for rec in self:
            rec.with_vouchers = bool(self.picking_ids[:1].batch_id.voucher_ids)

    @api.onchange('picking_ids')
    def set_book_domain(self):
        picking = self._get_pickings()
        if not picking:
            return {}
        else:
            return {'domain': {'book_id': [('company_id', '=', picking.company_id.id)]}}

    @api.onchange('book_id', 'picking_ids')
    def get_estimated_number_of_pages(self):
        lines_per_voucher = self.lines_per_voucher
        if lines_per_voucher == 0:
            self.estimated_number_of_pages = 1
            return

        operations = len(self.picking_ids.move_line_ids)
        estimated_number_of_pages = int(
            -(-float(operations) // float(lines_per_voucher)))
        self.estimated_number_of_pages = estimated_number_of_pages

    def do_print_voucher(self):
        self.printed = True
        if self.book_id:
            self.picking_ids[:1].batch_id.book_id = self.book_id.id
        return self.do_print_batch_vouchers(self.picking_ids[:1].batch_id)

    def do_print_and_assign(self):
        # We override the method to avoid assignation
        if self.book_id.lines_per_voucher != 0:
            return {
                'actions': [
                    {'type': 'ir.actions.act_window_close'},
                        self.with_context(batch=True).do_print_voucher(),
                ],
                'type': 'ir.actions.act_multi'
            }
        self.picking_ids[:1].batch_id.assign_numbers(1,self.book_id)
        return self.do_print_batch_vouchers(self.picking_ids[:1].batch_id)
    
    def do_print_batch_vouchers(self, batch):
        '''This function prints the voucher'''
        return self.env.ref('stock_batch_picking_voucher.batch_picking_preprinted').report_action(batch)
    
    def do_clean(self):
        batch = self.picking_ids[:1].batch_id
        batch.voucher_ids.unlink()
        batch.book_id = False
        batch.message_post(body=_('The assigned voucher were deleted'))
