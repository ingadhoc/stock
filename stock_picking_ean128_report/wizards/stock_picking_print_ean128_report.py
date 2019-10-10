##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, api, models


class StockPickingEan128Report(models.TransientModel):
    _name = 'stock.picking.print_ean128_report'
    _description = 'Stock Picking Print EAN128 Report'

    stock_picking_line_ids = fields.One2many(
        'stock.picking.print_ean128_report_detail',
        'stock_picking_report_id',
        'Product Print',
        default=lambda self: self._get_stock_picking_line(),
    )

    @api.model
    def _get_stock_picking_line(self):
        active_id = self._context.get('active_id', False)
        picking = self.env['stock.picking'].browse(active_id)
        if picking.move_line_ids:
            lines = []
            for line in picking.move_line_ids.filtered('lot_id'):
                values = {
                    'product_id': line.product_id.id,
                    'quantity': line.qty_done,
                    'lot_id': line.lot_id.id,
                    'product_uom_id': line.product_uom_id.id,
                    'move_line_id': line.id,
                }
                lines.append((0, 0, values))
            return lines
        return False

    @api.multi
    def do_print_report(self):
        self.ensure_one()
        action = self.env['ir.actions.report'].search(
            [('report_name', '=', 'report_stock_picking_EAN128')],
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
            [('report_name', '=', 'report_stock_picking_EAN128_excel')],
            limit=1).report_action(self)
        return {
            'actions': [
                {'type': 'ir.actions.act_window_close'},
                action,
            ],
            'type': 'ir.actions.act_multi',
        }
