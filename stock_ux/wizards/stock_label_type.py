# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, _, api, exceptions, fields, models


class ProductLabelLayout(models.TransientModel):
    _inherit = "product.label.layout"

    picking_id = fields.Many2one("stock.picking", string="Picking")
    from_template = fields.Boolean()
    line_ids = fields.One2many("stock.picking.zpl.lines", "picking_zpl_id", string="Moves")
    product_line_ids = fields.One2many("stock.product.zpl.lines", "wizard_id", string="Products")
    zpl_template = fields.Selection(
        selection_add=[("zpl_5x25", "ZPL 5 x 2,5 cm")],
        ondelete={"zpl_5x25": "set default"},
    )

    @api.model
    def default_get(self, default_fields):
        rec = super().default_get(default_fields)
        active_ids = self.env.context.get("active_ids") or self.env.context.get("active_id")
        active_model = self.env.context.get("active_model")
        if active_model == "stock.picking":
            picking = self.env["stock.picking"].browse(active_ids)
            rec["picking_id"] = picking.id
            rec["line_ids"] = self._line_commands_from_moves(picking.move_ids)
            return rec
        # Called from action_open_label_layout (e.g. via picking.label.type lot wizard).
        # Context has default_move_ids instead of active_model.
        move_ids_ctx = self.env.context.get("default_move_ids", [])
        if move_ids_ctx:
            moves = self.env["stock.move"].browse(move_ids_ctx)
            picking = moves.mapped("picking_id")
            if len(picking) == 1:
                rec["picking_id"] = picking.id
                rec["line_ids"] = self._line_commands_from_moves(moves)
                return rec
        # Support opening from product views (via Print Labels button).
        # product_ids / product_tmpl_ids come from the action context as plain ID lists.
        product_ids = self.env.context.get("default_product_ids", [])
        product_tmpl_ids = self.env.context.get("default_product_tmpl_ids", [])
        if product_ids:
            products = self.env["product.product"].browse(product_ids)
            rec["product_line_ids"] = [Command.create({"product_id": p.id, "quantity": 1}) for p in products]
        elif product_tmpl_ids:
            products = self.env["product.template"].browse(product_tmpl_ids).product_variant_ids
            rec["product_line_ids"] = [Command.create({"product_id": p.id, "quantity": 1}) for p in products]
            if len(products) > 1:
                rec["from_template"] = True
        return rec

    def _line_commands_from_moves(self, moves):
        """Build Command.create list for line_ids (done qty > 0 only)."""
        return [
            Command.create({"move_id": m.id, "move_quantity": m.quantity, "move_uom_id": m.product_uom.id})
            for m in moves.filtered(lambda m: m.quantity > 0)
        ]

    def process(self):
        """Intercept the standard Print button to use our custom ZPL report when selected."""
        self.ensure_one()
        if self.zpl_template == "zpl_5x25":
            if self.picking_id:
                return self.action_print()
            return self.action_print_product_zpl()
        return super().process()

    def _prepare_report_data(self):
        """When in picking context with per-product custom quantities, use line_ids values."""
        xml_id, data = super()._prepare_report_data()
        if self.picking_id and self.move_quantity == "custom" and self.line_ids:
            qty_map = {}
            for line in self.line_ids:
                pid = line.move_id.product_id.id
                qty_map[pid] = qty_map.get(pid, 0) + int(line.move_quantity)
            data["quantity_by_product"] = qty_map
        return xml_id, data

    def action_print(self):
        self.ensure_one()
        # Ensure line_ids have move_id set. When move_quantity == 'move' the table
        # is hidden so it's never submitted; in that case (or if move_id was lost),
        # rebuild from move_ids which Odoo populates via action_open_label_layout context.
        if not self.line_ids.filtered(lambda l: l.move_id) and self.move_ids:
            self.line_ids = self._line_commands_from_moves(self.move_ids)
        report_action = self.env.ref("stock_ux.action_custom_barcode_transfer_template_view_zpl").report_action(
            self.ids
        )
        report_action["close_on_report_download"] = True
        return report_action

    def action_print_product_zpl(self):
        self.ensure_one()
        # For single product (product.product): sync native Copies field into the line.
        # For product.template: per-variant quantities are edited directly in the table.
        if not self.from_template and self.custom_quantity and self.product_line_ids:
            self.product_line_ids.write({"quantity": self.custom_quantity})
        report_action = self.env.ref("stock_ux.action_product_barcode_zpl").report_action(self.ids)
        report_action["close_on_report_download"] = True
        return report_action


class StockPickingZplLines(models.TransientModel):
    _name = "stock.picking.zpl.lines"
    _description = "Stock Picking ZPL Label Lines"

    picking_zpl_id = fields.Many2one("product.label.layout")
    move_id = fields.Many2one("stock.move")
    move_quantity = fields.Float()
    move_uom_id = fields.Many2one("uom.uom")
    name = fields.Char(related="move_id.product_id.display_name", string="Product")

    @api.constrains("move_quantity")
    def _check_move_quantity(self):
        """Validate quantity doesn't exceed available quantity"""
        for line in self:
            if line.move_quantity > line.move_id.quantity:
                raise exceptions.ValidationError(
                    _(
                        f"The quantity to print ({line.move_quantity}) cannot be greater than the original quantity ({line.move_id.quantity})."
                    )
                )


class StockProductZplLines(models.TransientModel):
    _name = "stock.product.zpl.lines"
    _description = "Product ZPL Label lines"

    wizard_id = fields.Many2one("product.label.layout", required=True, ondelete="cascade")
    product_id = fields.Many2one("product.product", required=True)
    product_name = fields.Char(related="product_id.display_name", string="Variant")
    quantity = fields.Integer(default=1, required=True)
