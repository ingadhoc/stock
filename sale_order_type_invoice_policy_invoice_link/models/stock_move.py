
from odoo.addons.stock_picking_invoice_link.models.stock_move import StockMove


def new_write(self, vals):
    # monkey patch to take in consideration both module stock_picking_invoice_link and sale_order_type_invoice_policy   
    if "product_uom_qty" in vals and not self.env.context.get(
        "bypass_stock_move_update_restriction"
    ):
        for move in self:
            if move.state == "done" and move.invoice_line_ids:
                raise UserError(_("You can not modify an invoiced stock move"))
    res = super(StockMove, self).write(vals)
    if vals.get("state", "") == 'done':
            stock_moves = self.get_moves_delivery_link_invoice()
            for stock_move in stock_moves.filtered(lambda sm: sm.sale_line_id and (sm.sale_line_id.order_id.type_id.invoice_policy == "order" or sm.sale_line_id.order_id.type_id.invoice_policy == "by_product" and sm.product_id.invoice_policy == "order")):
                inv_type = stock_move.to_refund and "out_refund" or "out_invoice"
                inv_line = (self.env["account.move.line"].sudo().search([('sale_line_ids','=',stock_move.sale_line_id.id),('move_id.move_type','=',inv_type)]))
                if inv_line:
                    stock_move.invoice_line_ids = [(4, m.id) for m in inv_line]
    return res

StockMove.write = new_write
