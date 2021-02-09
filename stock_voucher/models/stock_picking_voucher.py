##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError


class StockPickingVoucher(models.Model):
    _name = 'stock.picking.voucher'
    _description = 'Stock Voucher Book'
    # _rec_name = 'number'

    # we keep this for report compatibility
    number = fields.Char(
        related='name',
        string='Number (for backward compatibility)',
    )
    # because m2m tags widget send only values to name field
    name = fields.Char(
        'Number',
        copy=False,
        required=True,
    )
    book_id = fields.Many2one(
        'stock.book',
        'Voucher Book',
    )
    picking_id = fields.Many2one(
        'stock.picking',
        'Picking',
        ondelete='cascade',
        required=True,
        index=True,
    )
    company_id = fields.Many2one(
        'res.company',
        'Company',
        related='picking_id.company_id',
    )
    # constraint de que el book y el picking deben ser de la misma company

    _sql_constraints = [
        ('voucher_number_uniq', 'unique(name, book_id)',
            _('The field "Number" must be unique per book.'))]

    @api.model
    def _format_document_number(self, document_number):
        """ Make validation of Argentinan Voucher
          * making validations on the document_number. If it is wrong it should raise an exception
          * format the document_number against a pattern and return it
        """
        if not document_number:
            return False
        msg = "'%s' " + _("is not a valid value for") + " '%s'.%s"
        failed = False
        args = document_number.split('-')
        if len(args) != 2:
            failed = True
        else:
            pos, number = args
            if len(pos) > 4 or not pos.isdigit():
                failed = True
            elif len(number) > 8 or not number.isdigit():
                failed = True
            document_number = '{:>04s}-{:>08s}'.format(pos, number)
        if failed:
            raise UserError(msg % (document_number, 'Voucher', _(
                'The document number must be entered with a dash (-) and a maximum of 4 characters for the first part'
                'and 8 for the second. The following are examples of valid numbers:\n* 1-1\n* 0001-00000001'
                '\n')))
        else:
            return document_number

    @api.constrains('name', 'picking_id')
    @api.onchange('name', 'picking_id')
    def check_voucher_number_unique(self):
        """
        Check internal pickings with voucher number unique
        """
        for rec in self.filtered(
                lambda x: x.picking_id.picking_type_id.code == 'incoming'):
            pick_type = rec.picking_id.picking_type_id
            name = self._format_document_number(rec.name)
            if name and name != rec.name:
                rec.name = name
            if pick_type.voucher_number_unique:
                rec._check_voucher_number_unique()

    def _check_voucher_number_unique(self):
        self.ensure_one()
        same_number_recs = self.search([
            ('picking_id.partner_id', '=',
                self.picking_id.partner_id.id),
            ('name', '=', self.name),
        ]) - self
        if same_number_recs:
            raise ValidationError(_(
                'Picking voucher number must be unique per '
                'partner'))
