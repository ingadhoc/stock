from odoo import Command, models


class StockMove(models.Model):
    _inherit = "stock.move"

    def write(self, vals):
        # bridge between stock_picking_invoice_link and sale_order_type_invoice_policy: link the invoice lines
        # also when the invoicing policy comes from the sale order type instead of from the product
        res = super().write(vals)
        if vals.get("state", "") == "done":
            stock_moves = self.get_moves_delivery_link_invoice()
            for stock_move in stock_moves.filtered(lambda sm: sm.sale_line_id):
                invoice_policy = stock_move.sudo().sale_line_id.order_id.type_id.invoice_policy
                if not (
                    invoice_policy == "order"
                    or (invoice_policy == "by_product" and stock_move.product_id.invoice_policy == "order")
                ):
                    continue
                inv_type = stock_move.to_refund and "out_refund" or "out_invoice"
                inv_line = (
                    self.env["account.move.line"]
                    .sudo()
                    .search([("sale_line_ids", "=", stock_move.sale_line_id.id), ("move_id.move_type", "=", inv_type)])
                )
                if inv_line:
                    stock_move.invoice_line_ids = [Command.link(line_id) for line_id in inv_line.ids]
        return res
