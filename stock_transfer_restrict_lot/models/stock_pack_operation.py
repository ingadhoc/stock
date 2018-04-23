##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api


class StockPackOperationLot(models.Model):

    _inherit = 'stock.pack.operation.lot'

    code = fields.Selection(
        related='operation_id.code'
    )


class StockPackOperation(models.Model):

    _inherit = 'stock.pack.operation'

    code = fields.Selection(
        related='picking_id.picking_type_id.code',
        string='Operation Type',
        readonly=True)

    @api.multi
    @api.constrains('pack_lot_ids')
    def validate_quantity(self):
        for rec in self:
            if rec.code != 'incoming' and rec.pack_lot_ids:
                for pack in rec.pack_lot_ids:
                    domain = [
                        ('location_id', '=', rec.location_id.id), '|',
                        ('reservation_id', '=', False),
                        ('reservation_id.picking_id', '=', rec.picking_id.id)]
                    pack.lot_id.validate_lot_quantity(
                        pack.qty, domain)
