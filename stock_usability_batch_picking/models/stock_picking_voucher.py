##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, api, _
from odoo.exceptions import ValidationError


class StockPickingVoucher(models.Model):
    _inherit = 'stock.picking.voucher'

    @api.multi
    def _check_voucher_number_unique(self):
        """
        We modify it to make it unique per batch (if available) or per
        pikcing
        """
        self.ensure_one()
        if self.picking_id.batch_picking_id:
            same_number_recs = self.search([
                ('picking_id.partner_id', '=',
                    self.picking_id.partner_id.id),
                ('name', '=', self.name),
                ('picking_id.batch_picking_id', '!=',
                    self.picking_id.batch_picking_id.id),
                ('id', '!=', self.id),
            ])
            if same_number_recs:
                raise ValidationError(_(
                    'Picking voucher number must be unique per '
                    'partner'))

        else:
            return super(
                StockPickingVoucher, self)._check_voucher_number_unique()
