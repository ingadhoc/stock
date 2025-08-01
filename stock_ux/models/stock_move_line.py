##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    picking_create_user_id = fields.Many2one(
        "res.users",
        # vamos a traves de picking para legar mas rapido y no pasar por move
        related="picking_id.create_uid",
        string="Picking Creator",
    )
    picking_code = fields.Selection(
        related="picking_type_id.code",
    )
    picking_type_id = fields.Many2one(
        related="picking_id.picking_type_id",
        store=True,
    )
    product_uom_qty_location = fields.Float(
        compute="_compute_product_uom_qty_location",
        string="Net Quantity",
    )
    name = fields.Char(
        related="move_id.name",
        related_sudo=False,
    )
    origin_description = fields.Char(
        related="move_id.origin_description",
    )

    @api.depends_context("location")
    def _compute_product_uom_qty_location(self):
        location = self._context.get("location")
        if not location:
            self.update({"product_uom_qty_location": 0.0})
            return False
        # because now we use location_id to select location, we have compelte
        # location name. If y need we can use some code of
        # _get_domain_locations on stock/product.py
        location_name = location[0]
        if isinstance(location[0], int):
            location_name = self.env["stock.location"].browse(location[0]).name
        locations = self.env["stock.location"].search([("complete_name", "ilike", location_name)])
        for rec in self:
            product_uom_qty_location = rec.quantity
            if rec.location_id in locations:
                # if location is source and destiny, then 0
                product_uom_qty_location = 0.0 if rec.location_dest_id in locations else -rec.quantity
            rec.product_uom_qty_location = product_uom_qty_location

    @api.constrains("quantity")
    def _check_manual_lines(self):
        if self._context.get("put_in_pack", False):
            return
        if any(
            self.filtered(
                lambda x: not x.location_id.should_bypass_reservation()
                and x.picking_id.picking_type_id.block_manual_lines
                and x._check_quantity_available() < 0
            )
        ):
            raise ValidationError(_("You can't transfer more quantity than the quantity on stock!"))

    def _check_quantity_available(self):
        self.ensure_one()
        total_available = 0.0
        if (
            self.product_id.is_storable
            and not self.env.context.get("trigger_assign")
            and not self.env.context.get("from_inverse_qty_done")
            and not self.env.context.get("sale_automation")
            and (
                self.picking_id.id in self.env.context.get("picking_ids", [])
                or not self.env.context.get("picking_ids", [])
            )
        ):
            locations = self.env["stock.location"].search(
                [("id", "child_of", self.picking_id.location_id.id), ("company_id", "=", self.picking_id.company_id.id)]
            )
            quants = self.env["stock.quant"].search(
                [("product_id", "=", self.product_id.id), ("location_id", "in", locations.ids)]
            )
            total_available = sum(quants.mapped("available_quantity")) - self.quantity
        return total_available

    @api.model_create_multi
    def create(self, vals_list):
        """This is to solve a bug when create the sml (the value is not completed after creation)
        and should be reported to odoo to solve."""
        recs = super().create(vals_list)
        for rec in recs:
            if rec.picking_id and not rec.description_picking:
                product = rec.product_id.with_context(lang=rec.picking_id.partner_id.lang or rec.env.user.lang)
                rec.description_picking = product._get_description(rec.picking_id.picking_type_id)
        return recs

    def _get_aggregated_product_quantities(self, **kwargs):
        aggregated_move_lines = super()._get_aggregated_product_quantities(**kwargs)
        use_origin = (
            self.env["ir.config_parameter"].sudo().get_param("stock_ux.delivery_slip_use_origin", "False") == "True"
        )
        if use_origin:
            move_line_by_move = {}
            for sml in self:
                move = sml.move_id
                if move and move.origin_description:
                    move_line_by_move.setdefault(
                        move.id, {"description": move.origin_description, "product_id": sml.product_id.id}
                    )
            used_moves = set()
            for line_data in aggregated_move_lines.values():
                for move_id, move_info in move_line_by_move.items():
                    if move_info["product_id"] == line_data["product"].id and move_id not in used_moves:
                        line_data["description"] = False
                        line_data["name"] = move_info["description"]
                        used_moves.add(move_id)
                        break

        return aggregated_move_lines

    def _inverse_qty_done(self):
        """
        It uses the `from_inverse_qty_done` context key to indicate that the update originates from
        this method.
        """
        for line in self:
            line.with_context(from_inverse_qty_done=True).quantity = line.qty_done
            line.picked = line.quantity > 0

    def _get_aggregated_properties(self, move_line=False, move=False):
        use_origin = (
            self.env["ir.config_parameter"].sudo().get_param("stock_ux.delivery_slip_use_origin", "False") == "True"
        )
        if use_origin:
            move = move or move_line.move_id
            uom = move.product_uom or move_line.product_uom_id
            name = move.product_id.display_name
            description = move.origin_description or ""
            product = move.product_id
            if description.startswith(name):
                description = description.removeprefix(name).strip()
            elif description.startswith(product.name):
                description = description.removeprefix(product.name).strip()
            line_key = (
                f"{product.id}_{product.display_name}_{description or ''}_{uom.id}_{move.product_packaging_id or ''}"
            )
            bom_line = getattr(move, "bom_line_id", False)
            if bom_line and bom_line.bom_id:
                bom = bom_line.bom_id
                line_key += f"_{bom.id if bom else ''}"
            else:
                bom = False
            return {
                "line_key": line_key,
                "name": name,
                "description": description,
                "product_uom": uom,
                "move": move,
                "packaging": move.product_packaging_id,
                "bom": bom,
            }
        else:
            return super()._get_aggregated_properties(move_line=move_line, move=move)
