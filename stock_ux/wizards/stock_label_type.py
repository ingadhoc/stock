# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, api, exceptions, fields, models


class ProductLabelLayout(models.TransientModel):
    _inherit = "product.label.layout"

    picking_id = fields.Many2one("stock.picking", string="Picking")
    line_ids = fields.One2many("stock.picking.zpl.lines", "picking_zpl_id", string="Moves")
    print_format = fields.Selection(
        selection_add=[("zpl_custom", "ZPL 2,5 x 5")],
        ondelete={"zpl_custom": "set default"},
    )
    zpl_template = fields.Selection(
        selection_add=[("custom_25x5", "ZPL 2,5 x 5")],
        ondelete={"custom_25x5": "set default"},
    )

    @api.model
    def default_get(self, default_fields):
        """Initialize wizard with picking data if called from picking"""
        rec = super().default_get(default_fields)
        active_model = self.env.context.get("active_model")

        if active_model == "stock.picking":
            active_ids = self.env.context.get("active_ids") or self.env.context.get("active_id")
            picking = self.env[active_model].browse(active_ids)
            rec["picking_id"] = picking.id if picking else False

            # Create lines for each move with quantity > 0
            move_ids = picking.mapped("move_ids").filtered(lambda x: x.quantity > 0)
            rec["line_ids"] = [
                Command.create({"move_id": x.id, "move_quantity": x.quantity, "move_uom_id": x.product_uom.id})
                for x in move_ids
            ]
        return rec

    def _get_line_quantities(self):
        """
        Get editable quantities from line_ids.
        Workaround: TransientModel doesn't persist Many2one correctly,
        so we match lines to moves by position.
        """
        quantity_map = {}
        if not self.line_ids or not self.picking_id:
            return quantity_map

        moves = self.picking_id.move_ids.filtered(lambda m: m.quantity > 0).sorted("id")
        lines = self.line_ids.sorted("id")

        for idx, line in enumerate(lines):
            if idx < len(moves):
                quantity_map[moves[idx].id] = int(line.move_quantity or 0)

        return quantity_map

    def _generate_zpl_label(self, product_name, barcode, is_first):
        """Generate a single ZPL label (left or right side)"""
        if is_first:
            return f"""^XA
^CI28
^LH0,0
^FO20,10,0

^FO10,40
^A0N,40,30
^TBN,360,40
^FD{product_name}^FS

^FO10,90
^BY3
^BCN,60,Y,N,N,A
^FD{barcode}^FS
"""
        else:
            return f"""^FX Nueva etiqueta
^LH445,0
^FO20,10,0
^FO10,40
^A0N,40,30
^TBN,360,40
^FD{product_name}^FS
^FO10,90
^BY3
^BCN,60,Y,N,N,A
^FD{barcode}^FS
^XZ
"""

    def _generate_zpl_content(self):
        """Generate ZPL for picking - 2 labels per row"""
        zpl_output = ""
        label_counter = 0
        quantity_map = self._get_line_quantities()

        for move in self.picking_id.move_ids.filtered(lambda m: m.quantity > 0):
            product = move.product_id
            product_name = product.display_name or ""
            barcode = product.barcode or product.default_code or ""
            quantity = quantity_map.get(move.id, int(max(move.quantity or 0, move.product_uom_qty or 0)))

            for _ in range(quantity):
                label_counter += 1
                is_first_of_pair = label_counter % 2 != 0
                zpl_output += self._generate_zpl_label(product_name, barcode, is_first_of_pair)

        # Close last label if odd number
        if label_counter % 2 != 0:
            zpl_output += " ^PQ1,0,1,Y^XZ "

        return zpl_output

    def _generate_zpl_from_products(self):
        """Generate ZPL for products - 2 labels per row"""
        zpl_output = ""
        label_counter = 0

        for product_line in self.product_ids:
            product = product_line.product_id
            product_name = product.display_name or ""
            barcode = product.barcode or product.default_code or ""
            quantity = int(product_line.quantity or 0)

            for _ in range(quantity):
                label_counter += 1
                is_first_of_pair = label_counter % 2 != 0
                zpl_output += self._generate_zpl_label(product_name, barcode, is_first_of_pair)

        # Close last label if odd number
        if label_counter % 2 != 0:
            zpl_output += " ^PQ1,0,1,Y^XZ "

        return zpl_output

    def _create_zpl_attachment(self, zpl_content, filename):
        """Create attachment and return download action"""
        import base64

        attachment = self.env["ir.attachment"].create(
            {
                "name": filename,
                "datas": base64.b64encode(zpl_content.encode("utf-8")),
                "mimetype": "text/plain",
                "res_model": self._name,
                "res_id": self.id,
            }
        )

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }

    def action_print(self):
        """Print labels in selected format"""
        self.ensure_one()

        # Handle custom ZPL format
        use_custom_zpl = self.print_format == "zpl_custom" or (
            self.print_format in ["zpl", "zplxprice"] and self.zpl_template == "custom_25x5"
        )

        if use_custom_zpl:
            if self.picking_id:
                zpl_content = self._generate_zpl_content()
                filename = f"Labels_{self.picking_id.name}.zpl"
            else:
                zpl_content = self._generate_zpl_from_products()
                filename = "Labels_Products.zpl"

            return self._create_zpl_attachment(zpl_content, filename)

        # Default Odoo behavior for other formats
        return super().action_print()


class StockPickingZplLines(models.TransientModel):
    _name = "stock.picking.zpl.lines"
    _description = "ZPL Label Lines for Picking"

    picking_zpl_id = fields.Many2one("product.label.layout", required=True, ondelete="cascade")
    move_id = fields.Many2one("stock.move", required=True, ondelete="cascade")
    move_quantity = fields.Float(required=True, string="Quantity")
    move_uom_id = fields.Many2one("uom.uom", string="UoM")
    product_name = fields.Char(string="Product", compute="_compute_product_name", store=False)

    @api.depends("move_id")
    def _compute_product_name(self):
        """Display product name (doesn't work in transient but needed for tree view)"""
        for line in self:
            line.product_name = line.move_id.product_id.display_name if line.move_id else ""

    @api.constrains("move_quantity")
    def _check_move_quantity(self):
        """Validate quantity doesn't exceed available quantity"""
        for line in self:
            if not line.move_id:
                continue

            max_qty = max(line.move_id.quantity or 0, line.move_id.product_uom_qty or 0)
            if max_qty > 0 and line.move_quantity > max_qty:
                raise exceptions.ValidationError(
                    f"La cantidad a imprimir ({line.move_quantity}) no puede ser mayor "
                    f"que la cantidad disponible ({max_qty})."
                )
