##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare


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
        return super(StockMove, self.with_context(cancel_from_order=True, can_delete=True))._merge_moves(
            merge_into=merge_into
        )

    def _get_undone_push_rule(self):
        """Regla de push del movimiento que este espejo negativo viene a deshacer.

        Devuelve False si no aplica (movimiento positivo, sin destino final, con
        movimientos destino que el core tiene que re-encadenar, o sin un
        movimiento vivo del tramo siguiente al que netear).
        """
        self.ensure_one()
        if (
            float_compare(self.product_uom_qty, 0, precision_rounding=self.product_uom.rounding) >= 0
            or not self.location_final_id
            or self.location_dest_id == self.location_final_id
            or self.move_dest_ids
        ):
            return False
        undone = self.search(
            [
                ("id", "!=", self.id),
                ("group_id", "=", self.group_id.id),
                ("product_id", "=", self.product_id.id),
                ("location_id", "=", self.location_dest_id.id),
                ("location_dest_id", "=", self.location_final_id.id),
                ("state", "not in", ("draft", "done", "cancel")),
                ("rule_id.action", "=", "push"),
                ("product_uom_qty", ">", 0),
            ],
            limit=1,
        )
        return undone.rule_id

    def _push_apply(self):
        """El espejo negativo hereda la puerta del movimiento que deshace.

        El core empuja el movimiento positivo en `_action_done` (ya con move
        lines y con el transportista propagado al picking) y el espejo negativo
        del cancel-remanente en `_action_confirm` (todavia sin move lines). Si la
        regla de push discrimina por `push_domain`, las dos evaluaciones pueden
        resolver reglas distintas: el negativo nace en otro tipo de operacion, no
        llega a ser candidato del merge, no netea y termina materializado como
        contra-entrega, dejando el movimiento original huerfano (tarea 73048 /
        ticket 124472).

        Cuando el tramo siguiente ya existe y esta vivo, la puerta no se vuelve a
        decidir: se reusa la regla con la que el core creo ese movimiento.
        """
        inherited = {}
        for move in self:
            rule = move._get_undone_push_rule()
            if rule:
                inherited[move.id] = rule
        if not inherited:
            return super()._push_apply()
        new_moves = super(StockMove, self.filtered(lambda m: m.id not in inherited))._push_apply()
        for move_id, rule in inherited.items():
            new_move = rule._run_push(self.browse(move_id))
            if new_move:
                new_moves |= new_move.sudo()._action_confirm()
        return new_moves

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
