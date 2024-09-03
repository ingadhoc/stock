from odoo import fields, api, models, Command


class StockPickingZpl(models.TransientModel):
    _name = 'stock.picking.zpl'
    _description = "Print Stock Voucher"

    picking_id = fields.Many2one('stock.picking',string='picking')
    line_ids = fields.One2many('stock.picking.zpl.lines','picking_zpl_id', string='Moves')

    @api.model
    def default_get(self, default_fields):
        rec = super().default_get(default_fields)
        active_ids = self._context.get('active_ids') or self._context.get('active_id')
        active_model = self._context.get('active_model')
        if active_model == 'stock.picking':
            move_ids = self.env[active_model].browse(active_ids).mapped('move_ids').filtered(lambda x: x.quantity > 0 )
            rec['line_ids'] = [Command.create({'move_id': x.id, 'move_quantity':x.quantity}) for x in move_ids]
        return rec

    def action_print(self):
        self.ensure_one()
        report_id = self.env.ref("stock_ux.custom_label_transfer_template_view_zpl")
        report_action = report_id.report_action(self.ids)
        report_action['close_on_report_download']=True
        return report_action

class StockPickingZplLines(models.TransientModel):
    _name = 'stock.picking.zpl.lines'
    _description = "Print Stock Voucher lines"

    picking_zpl_id = fields.Many2one('stock.picking.zpl')

    move_id = fields.Many2one('stock.move')

    move_quantity = fields.Float()

    name = fields.Char(related='move_id.name')
