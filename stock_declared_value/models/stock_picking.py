##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    declared_value = fields.Float(
        digits="Account",
        compute="_compute_declared_value",
        store=True,
        readonly=False,
    )

    @api.depends(
        "move_ids.state",
        "move_ids.quantity",
    )
    def _compute_declared_value(self):
        for rec in self.filtered(
            lambda p: p.picking_type_id.automatic_declare_value and p.state not in ["done", "cancel"]
        ):
            done_value = 0.0
            picking_value = 0.0
            inmediate_transfer = True
            pricelist = False
            stock_bom_lines = self.env["stock.move"]
            moves = rec.move_ids.filtered(lambda x: x.state != "cancel")
            # While _action_done runs, the picking still holds the moves that are about
            # to be split off into the backorder: stock.move._create_backorder already
            # created and confirmed them (so they are reserved when there is stock) and
            # stock.picking._create_backorder has not moved them out yet. Right in
            # between, _create_backorder_picking copies the picking and copy_data reads
            # this field, forcing the pending recomputation. Counting those moves would
            # declare what was shipped plus what the backorder reserved, and the state
            # filter above would then freeze that value. Once a move is done, only the
            # done ones are what this voucher actually ships.
            done_moves = moves.filtered(lambda x: x.state == "done")
            if done_moves:
                moves = done_moves
            for move_line in moves:
                order_line = move_line.sale_line_id
                if move_line.quantity:
                    inmediate_transfer = False
                if order_line:
                    pricelist = rec.sale_id.pricelist_id
                    # this should happens only if on SO it's a bom kit
                    if not order_line.product_id == move_line.product_id:
                        stock_bom_lines |= move_line
                        continue
                    so_product_qty = move_line.product_uom_qty
                    so_qty_done = move_line.quantity
                    # convert quantities if move line uom and sale line uom
                    # are different
                    if move_line.product_uom != order_line.product_uom_id:
                        so_product_qty = move_line.product_uom._compute_quantity(
                            move_line.product_uom_qty, order_line.product_uom_id
                        )
                        so_qty_done = move_line.product_uom._compute_quantity(
                            move_line.quantity, order_line.product_uom_id
                        )
                    picking_value += order_line.price_reduce_taxexcl * so_product_qty
                    done_value += order_line.price_reduce_taxexcl * so_qty_done
                elif rec.picking_type_id.pricelist_id:
                    pricelist = rec.picking_type_id.pricelist_id
                    price = rec.picking_type_id.pricelist_id.with_context(uom=move_line.product_uom.id)._price_get(
                        move_line.product_id, move_line.quantity or 1.0, partner=rec.partner_id.id
                    )[rec.picking_type_id.pricelist_id.id]
                    picking_value += price * move_line.product_uom_qty
                    done_value += price * move_line.quantity

            # This is for product in a kit (should only happen if sale_mrp is
            # installed). If it is bom we only compute amount if all bom
            # components are delivered (same as in bom _get_delivered_qty)
            bom_enable = "bom_ids" in self.env["product.template"]._fields
            if bom_enable:
                for so_bom_line in stock_bom_lines.mapped("sale_line_id"):
                    bom = self.env["mrp.bom"]._bom_find(products=so_bom_line.product_id)[so_bom_line.product_id]
                    if bom and bom.type == "phantom":
                        bom_moves = so_bom_line.move_ids & stock_bom_lines._origin
                        done_avg = []
                        picking_avg = []
                        # Explode for 1 kit to get base quantities per component
                        boms, lines = bom.sudo().explode(so_bom_line.product_id, 1.0, picking_type=bom.picking_type_id)
                        for move in bom_moves:
                            bom_quantity = 0.0
                            for bom_line, line_data in lines:
                                if bom_line.product_id == move.product_id:
                                    bom_quantity += line_data["qty"]
                            if not bom_quantity:
                                continue
                            rec_move = rec.move_ids.filtered(lambda m: m._origin.id == move.id)
                            if not rec_move:
                                continue
                            picking_avg.append(move.product_uom_qty / bom_quantity)
                            done_avg.append(rec_move.quantity / bom_quantity)
                        if picking_avg and done_avg:
                            # Average represents how many kits, multiply by unit price
                            picking_value += so_bom_line.price_reduce_taxexcl * (sum(picking_avg) / len(picking_avg))
                            done_value += so_bom_line.price_reduce_taxexcl * (sum(done_avg) / len(done_avg))

            declared_value = picking_value if inmediate_transfer else done_value
            if pricelist:
                # we convert the declared_value to the currency of the company
                rec.declared_value = pricelist.currency_id._convert(
                    declared_value,
                    rec.company_id.currency_id,
                    rec.company_id,
                    rec.sale_id.date_order or fields.Date.today(),
                )
            else:
                rec.declared_value = declared_value
