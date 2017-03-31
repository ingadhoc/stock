# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api, _
from openerp.exceptions import ValidationError


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
            print 'same_number_recs', same_number_recs
            if same_number_recs:
                raise ValidationError(_(
                    'Picking voucher number must be unique per '
                    'partner'))

        else:
            return super(
                StockPickingVoucher, self)._check_voucher_number_unique()
