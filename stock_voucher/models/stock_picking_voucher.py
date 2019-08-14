##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


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

    @api.constrains('name', 'picking_id')
    @api.onchange('name', 'picking_id')
    def check_voucher_number_unique(self):
        """
        Check internal pickings with voucher number unique
        """
        for rec in self.filtered(
                lambda x: x.picking_id.picking_type_id.code == 'incoming'):
            pick_type = rec.picking_id.picking_type_id
            name = pick_type.voucher_number_validator_id.validate_value(
                rec.name)
            if name and name != rec.name:
                rec.name = name
            if pick_type.voucher_number_unique:
                rec._check_voucher_number_unique()

    @api.multi
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
