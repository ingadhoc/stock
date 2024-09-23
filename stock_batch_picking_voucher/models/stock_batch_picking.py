##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, api, models, _
from odoo.exceptions import UserError

class StockPickingBatch(models.Model):
    _inherit = 'stock.picking.batch'

    voucher_ids = fields.One2many(
        'stock.picking.voucher',
        'batch_id',
        'Remitos',
        copy=False,
    )

    book_id = fields.Many2one(
        'stock.book',
        'Talonario',
        copy=False,
        ondelete='restrict',
        check_company=True
    )

    next_number = fields.Integer(
        related='book_id.next_number',
    )

    def assign_numbers(self, estimated_number_of_pages, book):
        self.ensure_one()
        list_of_vouchers = []
        for page in range(estimated_number_of_pages):
            list_of_vouchers.append({
                'name': book.sequence_id.next_by_id(),
                'book_id': book.id,
                'batch_id' : self.id,
            })
        self.env['stock.picking.voucher'].sudo().create(list_of_vouchers)
        self.message_post(body=_(
            'Números de remitos asignados: %s') % (self.voucher_ids.mapped("display_name")))
        self.write({'book_id': book.id})

        ############# Cambios post wizard, posible abstract #############
        
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
        
    @api.model
    def _get_book(self):
        return self.book_id or self.env['stock.book'].search([('company_id', '=', self.picking_ids[:1].company_id.id)], limit=1)
    
    @api.depends('picking_ids', 'picking_ids.voucher_ids')
    def _compute_with_vouchers(self):
        for rec in self:
            rec.with_vouchers = bool(self.voucher_ids)
    
    # def do_print_voucher(self):
    #     self.printed = True
    #     # if self.book_id:
    #     #     self.book_id = self.book_id.id
    #     return self.do_print_batch_vouchers()
    
    def do_print_and_assign(self):
        # We override the method to avoid assignation
        if not self.book_id:
            raise UserError("Primero debe setear un talonario")
        if self.book_id.lines_per_voucher != 0:
            self.printed = True
            return self.with_context(batch=True).do_print_batch_vouchers()
        self.assign_numbers(1,self.book_id)
        return self.do_print_batch_vouchers()
    
    def do_print_batch_vouchers(self):
        '''This function prints the voucher'''
        # self.env.ref('stock_batch_picking_voucher.batch_picking_preprinted').report_action(self)
        return self.env.ref('stock_batch_picking_voucher.batch_picking_preprinted').report_action(self)
    
    def do_clean(self):
        self.voucher_ids.unlink()
        # self.book_id = False
        self.message_post(body=_('The assigned voucher were deleted'))
