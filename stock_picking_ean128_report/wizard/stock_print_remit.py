# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, api, models


class StockLotEan128Report(models.TransientModel):

    _name = 'stock.lot.print_ean128_report'

    @api.model
    def _get_lot(self):
        active_id = self._context.get('active_id', False)
        return self.env['stock.production.lot'].browse(active_id)

    lot_id = fields.Many2one(
        'stock.production.lot', default=_get_lot)
    quantity = fields.Integer(string='Quantity', default=1)
    product_id = fields.Many2one(
        'product.product',
        related='lot_id.product_id',
        string="Product", readonly=True)

    @api.multi
    def do_print_report(self):

        self.ensure_one()
        return self.env['report'].get_action(
            self, 'report_stock_lot_EAN128')

    @api.multi
    def do_print_report_excel(self):

        self.ensure_one()
        return self.env['report'].get_action(
            self, 'report_stock_lot_EAN128_excel')


class StockPickingEan128ReportDetail(models.TransientModel):

    _name = 'stock.picking.print_ean128_report_detail'

    stock_picking_report_id = fields.Many2one(
        'stock.picking.print_ean128_report', 'Picking Report EAN Print')
    product_id = fields.Many2one(
        'product.product', string="Product", readonly=True)
    quantity = fields.Integer(string='Quantity')
    lot_id = fields.Many2one(
        'stock.production.lot', string='Lot', readonly=True)
    product_uom_id = fields.Many2one(
        'product.uom', string='UOM', readonly=True)


class StockPickingEan128Report(models.TransientModel):
    _name = 'stock.picking.print_ean128_report'

    @api.model
    def _get_stock_picking_line(self):
        active_id = self._context.get('active_id', False)
        picking = self.env['stock.picking'].browse(active_id)
        if picking.pack_operation_ids:
            lines = []
            for line in picking.pack_operation_ids:
                for pack in line.pack_lot_ids:
                    values = {
                        'product_id': line.product_id.id,
                        'quantity': pack.qty,
                        'lot_id': pack.lot_id.id,
                        'product_uom_id': line.product_uom_id.id,
                    }
                    lines.append((0, 0, values))
            return lines
        return False

    stock_picking_line_ids = fields.One2many(
        'stock.picking.print_ean128_report_detail',
        'stock_picking_report_id', 'Product Print',
        default=_get_stock_picking_line
    )

    @api.multi
    def do_print_report(self):

        self.ensure_one()
        return self.env['report'].get_action(
            self, 'report_stock_picking_EAN128')

    @api.multi
    def do_print_report_excel(self):

        self.ensure_one()
        return self.env['report'].get_action(
            self, 'report_stock_picking_EAN128_excel')
