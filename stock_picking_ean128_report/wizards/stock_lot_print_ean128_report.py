##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, api, models


class StockLotEan128Report(models.TransientModel):

    _name = 'stock.lot.print_ean128_report'
    _description = 'Stock Lot Print EAN128 Report'

    @api.model
    def _get_lot(self):
        active_id = self._context.get('active_id', False)
        return self.env['stock.production.lot'].browse(active_id)

    lot_id = fields.Many2one(
        'stock.production.lot',
        default=lambda self: self._get_lot(),
    )
    quantity = fields.Integer(
        default=1,
    )
    product_id = fields.Many2one(
        'product.product',
        related='lot_id.product_id',
    )

    @api.multi
    def do_print_report(self):
        self.ensure_one()
        action = self.env['ir.actions.report'].search(
            [('report_name', '=', 'report_stock_lot_EAN128')],
            limit=1).report_action(self)
        return {
            'actions': [
                {'type': 'ir.actions.act_window_close'},
                action,
            ],
            'type': 'ir.actions.act_multi',
        }

    @api.multi
    def do_print_report_excel(self):
        self.ensure_one()
        action = self.env['ir.actions.report'].search(
            [('report_name', '=', 'report_stock_lot_EAN128_excel')],
            limit=1).report_action(self)
        return {
            'actions': [
                {'type': 'ir.actions.act_window_close'},
                action,
            ],
            'type': 'ir.actions.act_multi',
        }
