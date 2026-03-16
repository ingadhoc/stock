# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, api, exceptions, fields, models


class ProductLabelLayout(models.TransientModel):
    _inherit = "product.label.layout"
    picking_id = fields.Many2one("stock.picking", string="picking")
    line_ids = fields.One2many("stock.picking.zpl.lines", "picking_zpl_id", string="Moves")
    product_line_ids = fields.One2many("stock.product.zpl.lines", "wizard_id", string="Products")

    @api.model
    def default_get(self, default_fields):
        rec = super().default_get(default_fields)
        active_ids = self.env.context.get("active_ids") or self.env.context.get("active_id")
        active_model = self.env.context.get("active_model")
        if active_model == "stock.picking":
            move_ids = self.env[active_model].browse(active_ids).mapped("move_ids").filtered(lambda x: x.quantity > 0)
            rec["line_ids"] = [
                Command.create({"move_id": x.id, "move_quantity": x.quantity, "move_uom_id": x.product_uom.id})
                for x in move_ids
            ]
            return rec
        # Support opening from product views (via Print Labels button).
        # product_ids / product_tmpl_ids come from the action context as plain ID lists.
        product_ids = self._context.get("default_product_ids", [])
        product_tmpl_ids = self._context.get("default_product_tmpl_ids", [])
        if product_ids:
            products = self.env["product.product"].browse(product_ids)
            rec["product_line_ids"] = [Command.create({"product_id": p.id, "quantity": 1}) for p in products]
        elif product_tmpl_ids:
            products = self.env["product.template"].browse(product_tmpl_ids).product_variant_ids
            rec["product_line_ids"] = [Command.create({"product_id": p.id, "quantity": 1}) for p in products]
        return rec

    def action_print(self):
        self.ensure_one()
        report_id = self.env.ref("stock_ux.action_custom_barcode_transfer_template_view_zpl")
        report_action = report_id.report_action(self.ids)
        report_action["close_on_report_download"] = True
        return report_action

    def action_print_pdf(self):
        self.ensure_one()
        report_id = self.env.ref("stock_ux.action_custom_label_transfer_template_view_pdf")
        report_action = report_id.report_action(self.ids)
        report_action["close_on_report_download"] = True
        return report_action

    def action_print_product_zpl(self):
        self.ensure_one()
        report_id = self.env.ref("stock_ux.action_product_barcode_zpl")
        report_action = report_id.report_action(self.ids)
        report_action["close_on_report_download"] = True
        return report_action


class StockPickingZplLines(models.TransientModel):
    _name = "stock.picking.zpl.lines"
    _description = "Print Stock Voucher lines"

    picking_zpl_id = fields.Many2one("product.label.layout")

    move_id = fields.Many2one("stock.move")

    move_quantity = fields.Float()

    move_uom_id = fields.Many2one("uom.uom")

    name = fields.Char(related="move_id.reference")

    @api.constrains("move_quantity")
    def _check_move_quantity(self):
        for line in self:
            if line.move_quantity > line.move_id.quantity:
                raise exceptions.ValidationError("La cantidad a imprimir no puede ser mayor que la cantidad original.")


class StockProductZplLines(models.TransientModel):
    _name = "stock.product.zpl.lines"
    _description = "Product ZPL Label lines"

    wizard_id = fields.Many2one("product.label.layout", required=True, ondelete="cascade")
    product_id = fields.Many2one("product.product", required=True)
    product_name = fields.Char(related="product_id.display_name", string="Producto")
    quantity = fields.Integer(default=1, required=True)
