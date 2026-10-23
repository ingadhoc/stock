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
        help="Quantity of this line relative to the location searched with the 'Net Quantity "
        "Location' filter: negative when the line leaves that location, positive when it enters, "
        "and 0 when it does not apply. Without that filter it is always 0 by design; the useful "
        "value is the column total at the bottom.",
    )
    origin_description = fields.Char(
        related="move_id.origin_description",
    )
    # el scheduled_date nativo es related a move_id.date, que al validar pasa a la fecha de proceso
    picking_scheduled_date = fields.Datetime(
        related="picking_id.scheduled_date",
        string="Transfer Scheduled Date",
        help="Scheduled date of the transfer, not replaced by the processing date once done.",
    )

    @api.depends_context("location")
    def _compute_product_uom_qty_location(self):
        location = self.env.context.get("location")
        if not location:
            self.update({"product_uom_qty_location": 0.0})
            return False
        # because now we use location_id to select location, we have compelte
        # location name. If y need we can use some code of
        # _get_domain_locations on stock/product.py
        location_name = location[0]
        if isinstance(location[0], int):
            # When the location is picked from the search dropdown, 'location' carries the record
            # id (int) instead of the typed text. stock.location has no 'reference' field, so we
            # resolve it through 'complete_name' (same field the ilike below matches against).
            location_name = self.env["stock.location"].browse(location[0]).complete_name
        locations = self.env["stock.location"].search([("complete_name", "ilike", location_name)])
        for rec in self:
            product_uom_qty_location = rec.quantity
            if rec.location_id in locations:
                # if location is source and destiny, then 0
                product_uom_qty_location = 0.0 if rec.location_dest_id in locations else -rec.quantity
            rec.product_uom_qty_location = product_uom_qty_location

    def _get_manual_lines_to_check(self):
        if self.env.context.get("put_in_pack", False):
            return self.browse()
        return self.filtered(
            lambda x: not x.location_id.should_bypass_reservation()
            and x.picking_id.picking_type_id.block_manual_lines
            and x._is_manual_line_check_needed()
        )

    def _check_manual_lines(self):
        lines = self._get_manual_lines_to_check()
        if any(line._check_quantity_available() < 0 for line in lines):
            raise ValidationError(_("You can't transfer more quantity than the quantity on stock!"))
        lines._check_manual_lines_lot()

    def _check_manual_lines_lot(self):
        """Odoo never reserves more of a serial than the location holds, so a line on a serial
        that is not there leaves the product total untouched and slips through that check."""
        for line in self.filtered(lambda x: x.lot_id and not x.product_uom_id.is_zero(x.quantity)):
            on_hand = line._get_lot_quantity_in_location()
            # a done line already took its quantity out of the location
            needed = 0.0 if line.state == "done" else line.quantity_product_uom
            if line.product_id.uom_id.compare(on_hand, needed) < 0:
                raise ValidationError(
                    _(
                        "You can't transfer the lot/serial number %(lot)s from %(location)s: "
                        "it has no stock there. Pick it from the location that holds it.",
                        lot=line.lot_id.name,
                        location=line.location_id.display_name,
                    )
                )

    def _get_lot_quantity_in_location(self):
        """On hand of the lot in the exact location of the line: validating takes it from that
        quant, a sublocation holding it does not count. Strict gather also brings the quants
        without lot; as when it takes the quantity, only those with stock count."""
        self.ensure_one()
        quants = (
            self.env["stock.quant"]
            .sudo()
            ._gather(
                self.product_id,
                self.location_id,
                lot_id=self.lot_id,
                package_id=self.package_id,
                owner_id=self.owner_id,
                strict=True,
            )
        )
        uom = self.product_id.uom_id
        return sum(quants.filtered(lambda q: q.lot_id or uom.compare(q.quantity, 0) > 0).mapped("quantity"))

    def _is_manual_line_check_needed(self):
        self.ensure_one()
        return (
            self.product_id.is_storable
            and not self.env.context.get("trigger_assign")
            and not self.env.context.get("from_inverse_qty_done")
            and not self.env.context.get("sale_automation")
            and (
                self.picking_id.id in self.env.context.get("picking_ids", [])
                or not self.env.context.get("picking_ids", [])
            )
        )

    def _check_quantity_available(self):
        self.ensure_one()
        total_available = 0.0
        if self._is_manual_line_check_needed():
            locations = self.env["stock.location"].search(
                [
                    ("id", "child_of", self.picking_id.location_id.id),
                    ("company_id", "=", self.picking_id.company_id.id),
                ]
            )
            quants = self.env["stock.quant"].search(
                [
                    ("product_id", "=", self.product_id.id),
                    ("location_id", "in", locations.ids),
                ]
            )
            total_available = sum(quants.mapped("available_quantity"))
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
        recs._check_manual_lines()
        return recs

    def write(self, vals):
        res = super().write(vals)
        # only the lot check: the product total runs on create, and here it would also
        # refuse moving a line to the location that does hold the lot
        if {"lot_id", "location_id"} & set(vals):
            self._get_manual_lines_to_check()._check_manual_lines_lot()
        return res

    def _inverse_qty_done(self):
        """
        It uses the `from_inverse_qty_done` context key to indicate that the update originates from
        this method.
        """
        for line in self:
            line.with_context(from_inverse_qty_done=True).quantity = line.qty_done
            line.picked = line.quantity > 0

    def _get_aggregated_properties(self, move_line=False, move=False):
        """Con delivery_slip_use_origin mostramos la descripción de origen en vez de la de la
        operación, pisando solo lo necesario sobre el dict del super."""
        properties = super()._get_aggregated_properties(move_line=move_line, move=move)
        use_origin = (
            self.env["ir.config_parameter"].sudo().get_param("stock_ux.delivery_slip_use_origin", "False") == "True"
        )
        picking = move_line.picking_id if move_line else (move.picking_id if move else False)
        move = move or move_line.move_id
        if not use_origin or not picking or not picking.origin or not move.origin_description:
            return properties

        product = move.product_id
        reference = product.display_name
        origin_description = move.origin_description

        add_product_name = (
            self.env["ir.config_parameter"].sudo().get_param("stock_ux.delivery_slip_add_product_name", "False")
            == "True"
        )

        # Clean the origin_description by removing product name prefix
        clean_description = origin_description
        if origin_description != reference:
            if origin_description.startswith(reference):
                clean_description = origin_description.removeprefix(reference).strip()
            elif origin_description.startswith(product.name):
                clean_description = origin_description.removeprefix(product.name).strip()

        if add_product_name and clean_description and clean_description != origin_description:
            name = f"{product.name} - {clean_description}"
        else:
            name = clean_description or origin_description

        properties.update(
            {
                "name": name,
                # el origen ya viaja en el nombre, no lo repetimos abajo
                "description": "",
                # sumamos el origen a la clave del super para no fusionar orígenes distintos
                "line_key": f"{properties['line_key']}_{name}",
            }
        )
        return properties
