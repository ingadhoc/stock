##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero


class StockMove(models.Model):
    _inherit = "stock.move"

    used_lots = fields.Char(
        compute="_compute_used_lots",
    )
    picking_create_user_id = fields.Many2one(
        "res.users",
        related="picking_id.create_uid",
        string="Picking Creator",
    )
    picking_dest_id = fields.Many2one(
        related="move_dest_ids.picking_id",
        string="Destination Transfer",
    )
    lots_visible = fields.Boolean(
        related="move_line_ids.lots_visible",
    )

    picking_partner_id = fields.Many2one(
        "res.partner",
        "Transfer Destination Address",
        related="picking_id.partner_id",
    )

    origin_description = fields.Char(compute="_compute_origin_description", compute_sudo=True)

    @api.depends(
        "move_line_ids.quantity",
        "move_line_ids.lot_id",
    )
    def _compute_used_lots(self):
        for rec in self:
            rec.used_lots = ", ".join(
                rec.move_line_ids.filtered("lot_id").mapped(lambda x: "%s (%s)" % (x.lot_id.name, x.quantity))
            )

    def _compute_origin_description(self):
        for rec in self:
            if rec.sale_line_id:
                rec.origin_description = rec.sale_line_id.name
            elif rec.picking_id.origin:
                rec.origin_description = rec.product_id.name
            else:
                rec.origin_description = rec.description_picking

    def action_view_linked_record(self):
        """This function returns an action that display existing sales order
        of given picking.
        """
        self.ensure_one()
        action_ref = self._context.get("action")
        form_view_ref = self._context.get("form_view")
        action = self.env["ir.actions.actions"]._for_xml_id(action_ref)
        form_view = self.env.ref(form_view_ref)
        res_id = self._context.get("res_id")
        action["views"] = [(form_view.id, "form")]
        action["res_id"] = res_id
        return action

    @api.model
    def default_get(self, fields_list):
        # We override the default_get to make stock moves created when the picking
        # was confirmed , this way restrict to add more quantity that initial demand
        defaults = super().default_get(fields_list)
        if self.env.context.get("default_picking_id"):
            picking_id = self.env["stock.picking"].browse(self.env.context["default_picking_id"])
            if picking_id.state == "confirmed":
                defaults["state"] = "confirmed"
                defaults["product_uom_qty"] = 0.0
                defaults["additional"] = True
        return defaults

    @api.constrains("state")
    def check_cancel(self):
        if self._context.get("cancel_from_order") or self.env.is_superuser():
            return
        if self.filtered(
            lambda x: (
                x.picking_id
                and x.state == "cancel"
                and not self.env.user.has_group("stock_ux.allow_picking_cancellation")
            )
        ):
            raise ValidationError("Only User with 'Picking cancelation allow' rights can cancel pickings")

    def _merge_moves(self, merge_into=False):
        # 22/04/2024: Agregamos esto porque sino al intentar confirmar compras con usuarios sin permisos, podia pasar que salga la constrain de arriba (check_cancel)
        # Agregamos can_delete=True para permitir el unlink de moves duplicados durante el merge
        moves = super(StockMove, self.with_context(cancel_from_order=True, can_delete=True))._merge_moves(
            merge_into=merge_into
        )
        return moves._merge_negative_moves_into_sibling_pickings()

    def _merge_negative_moves_into_sibling_pickings(self):
        """Absorb what core left of a negative move into pending moves of the same demand,
        instead of letting it become a phantom return."""
        neg_moves = self.filtered(
            lambda m: m.state not in ("done", "cancel")
            and m.group_id
            and float_compare(m.product_uom_qty, 0.0, precision_rounding=m.product_uom.rounding) < 0
        )
        if not neg_moves:
            return self
        # Fields that drift between a pending move and its negative mirror; the sale line and
        # the locations are compared by _carries_demand_of instead.
        relaxed = ["date", "date_deadline", "price_unit", "procure_method", "sale_line_id"]
        relaxed += ["location_id", "location_dest_id", "location_final_id", "created_purchase_request_line_id"]
        neg_key = self._merge_move_itemgetter(
            self._prepare_merge_moves_distinct_fields(),
            self._prepare_merge_negative_moves_excluded_distinct_fields() + relaxed,
        )
        merged_moves = moves_to_unlink = moves_to_cancel = self.env["stock.move"]
        reserved_before = {}
        for neg_move in neg_moves:
            key = neg_key(neg_move)
            candidates = (
                self.search(
                    [
                        ("group_id", "=", neg_move.group_id.id),
                        ("product_id", "=", neg_move.product_id.id),
                        ("picking_id", "!=", False),
                        ("state", "not in", ("draft", "done", "cancel")),
                    ]
                )
                .filtered(
                    lambda m: float_compare(m.product_uom_qty, 0.0, precision_rounding=m.product_uom.rounding) > 0
                    # Never undo what the warehouse already prepared.
                    and not m.picked
                    and neg_key(m) == key
                    and m._carries_demand_of(neg_move)
                )
                .sorted(lambda m: (m._is_in_progress_transfer(), m.state == "assigned", -m.id))
            )
            # Core's absorption, without its price averaging: the prices may differ here.
            for pos_move in candidates:
                reserved_before.setdefault(pos_move.id, pos_move.quantity)
                if (
                    float_compare(
                        pos_move.product_uom_qty,
                        abs(neg_move.product_uom_qty),
                        precision_rounding=pos_move.product_uom.rounding,
                    )
                    >= 0
                ):
                    pos_move.write(
                        {
                            "product_uom_qty": pos_move.product_uom_qty + neg_move.product_uom_qty,
                            "move_dest_ids": [
                                Command.link(m.id)
                                for m in neg_move.move_dest_ids
                                if m.location_id == pos_move.location_dest_id
                            ],
                            "move_orig_ids": [
                                Command.link(m.id)
                                for m in neg_move.move_orig_ids
                                if m.location_dest_id == pos_move.location_id
                            ],
                        }
                    )
                    merged_moves |= pos_move
                    moves_to_unlink |= neg_move
                    if float_is_zero(pos_move.product_uom_qty, precision_rounding=pos_move.product_uom.rounding):
                        moves_to_cancel |= pos_move
                    break
                neg_move.product_uom_qty += pos_move.product_uom_qty
                pos_move.product_uom_qty = 0
                moves_to_cancel |= pos_move
        (moves_to_unlink | moves_to_cancel)._clean_merged()
        if moves_to_unlink:
            moves_to_unlink._action_cancel()
            moves_to_unlink.sudo().unlink()
        moves_to_cancel._action_cancel()
        reduced = merged_moves - moves_to_cancel
        # Lowering the demand of a reserved move unreserves it; reserve what it still needs.
        reduced.filtered(lambda m: reserved_before.get(m.id) and m.state != "assigned")._action_assign()
        return (self | reduced) - moves_to_unlink

    def _is_in_progress_transfer(self):
        """Whether the warehouse already started on this move's transfer."""
        picking = self.picking_id
        return bool(
            picking.printed
            or ("batch_id" in picking._fields and picking.batch_id)
            or ("voucher_ids" in picking._fields and picking.voucher_ids)
        )

    def _carries_demand_of(self, neg_move):
        """Whether this pending move carries the demand that ``neg_move`` removes."""
        self.ensure_one()
        # Pull legs have no sale line of their own: compare the lines of their chains.
        lines, neg_lines = self._get_sale_order_lines(), neg_move._get_sale_order_lines()
        if (lines or neg_lines) and not lines & neg_lines:
            return False
        # A pull chain the mirror lacks (route changed): reducing it here would strand its next leg.
        if not neg_move.move_dest_ids and self.move_dest_ids.filtered(lambda m: m.state not in ("done", "cancel")):
            return False
        start, neg_start = self.location_id, neg_move.location_id
        end = self.location_final_id or self.location_dest_id
        neg_end = neg_move.location_final_id or neg_move.location_dest_id
        # Same leg, the source possibly moved to a sub-location. An empty final
        # location (migrated data) matches; a different one is another chain.
        same_leg = (
            start._child_of(neg_start)
            and self.location_dest_id == neg_move.location_dest_id
            and (
                not self.location_final_id
                or not neg_move.location_final_id
                or self.location_final_id == neg_move.location_final_id
            )
        )
        # Same end through another leg shape or source. A later leg under the stock location
        # must not pass for the first one: same exact start, or a first leg of the same type.
        same_start = start == neg_start or (self.picking_type_id == neg_move.picking_type_id and not self.move_orig_ids)
        same_trip = same_start and end._child_of(neg_end)
        return same_leg or same_trip

    def action_explode(self):
        # Cuando se explota un kit, MRP cancela y elimina el move original del producto kit,
        # aunque tenga sale_line_id. Permitimos ese unlink con can_delete=True.
        return super(StockMove, self.with_context(can_delete=True)).action_explode()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("picking_id", False):
                continue
            sp = self.env["stock.picking"].browse(vals["picking_id"])
            if (
                sp.picking_type_id.block_additional_quantity
                and sp.sale_id
                and (sp.sale_id.state == "sale" or sp.sale_id.state == "done")
            ):
                if vals.get("additional", False) and not vals.get("origin_returned_move_id"):
                    raise UserError(
                        "No se puede agregar productos adicionales ni modificar las cantidades demandadas:\n"
                        "- El pedido de venta se encuentra bloqueado.\n"
                        "- Está activado el bloqueo de cantidades adicionales."
                    )

        return super(StockMove, self).create(vals_list)

    @api.depends("state", "picking_id")
    def _compute_is_initial_demand_editable(self):
        super(StockMove, self)._compute_is_initial_demand_editable()
        for move in self:
            if move.picking_id.picking_type_id.block_additional_quantity and move.picking_id.state != "draft":
                move.is_initial_demand_editable = False

    def _trigger_assign(self):
        """To avoid to check_quantity_available when an assing in move is trigger we
        send a context that checks if the assign comes from this method
        """
        if not self.env.context.get("trigger_assign"):
            return super().with_context(trigger_assign=True)._trigger_assign()
        return super()._trigger_assign()

    def _action_assign(self, force_qty=False):
        """Reservar / Comprobar disponibilidad crea líneas de reserva, no líneas
        cargadas a mano, por lo que no debe dispararse el chequeo de
        _check_manual_lines. El _trigger_assign automático ya lo evitaba, pero el
        action_assign manual del picking no pasaba por ahí; marcamos el contexto
        para saltear _check_quantity_available al crear las stock.move.line.
        """
        return super(StockMove, self.with_context(trigger_assign=True))._action_assign(force_qty=force_qty)

    def _prepare_procurement_values(self):
        values = super()._prepare_procurement_values()
        physical_warehouse = self.location_id.warehouse_id
        propagated_warehouse = values.get("warehouse_id")
        is_subcontracting_move = (
            "raw_material_production_id" in self._fields
            and "subcontractor_id" in self.raw_material_production_id._fields
            and bool(self.raw_material_production_id.subcontractor_id)
        )

        # In some multi-warehouse MTO chains the move keeps the commercial
        # warehouse in `warehouse_id` even when the real source location belongs
        # to another warehouse. If we propagate that stale warehouse to the next
        # procurement, Odoo may reuse a draft RFQ from the wrong warehouse and
        # end up mixing destinations across warehouses in the same PO.
        # Scope the correction to MTO moves only so other procurement flows can
        # keep their intentional warehouse propagation.
        if (
            self.procure_method == "make_to_order"
            and not is_subcontracting_move
            and physical_warehouse
            and propagated_warehouse
            and propagated_warehouse != physical_warehouse
        ):
            values["warehouse_id"] = physical_warehouse

        return values

    @api.ondelete(at_uninstall=False)
    def _unlink_if_not_from_order(self):
        """
        Prevent deletion of moves linked to sale or purchase orders.
        Only manual moves (not from orders) can be deleted.
        Allow deletion when coming from internal Odoo processes (like merge_moves).
        """
        # Allow deletion when coming from internal processes
        if self.env.context.get("can_delete"):
            return

        protected_moves = self.env["stock.move"]

        # Check moves from sales (if sale_stock is installed)
        if "sale_line_id" in self._fields:
            protected_moves |= self.filtered(lambda m: m.sale_line_id)

        # Check moves from purchases (if purchase_stock is installed)
        if "purchase_line_id" in self._fields:
            protected_moves |= self.filtered(lambda m: m.purchase_line_id)

        if protected_moves:
            raise UserError(
                _(
                    "Cannot delete stock moves linked to sale or purchase orders.\n"
                    "Please modify quantities from the source order instead.\n\n"
                    "Affected moves: %s"
                )
                % ", ".join(protected_moves.mapped("display_name"))
            )
