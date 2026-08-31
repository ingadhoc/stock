##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"

    picking_type_code = fields.Selection(store=True)
    partner_id = fields.Many2one(
        "res.partner",
        # por ahora lo hacemos requerido porque si no tenemos que hacer algun
        # maneje en la vista para que si esta seteado pase dominio
        # y si no esta seteado no
        # required=True,
        help="If you choose a partner then only pickings of this partner will be sellectable",
    )
    voucher_number = fields.Char()
    voucher_required = fields.Boolean(
        # related='picking_type_id.voucher_required',
        compute="_compute_picking_type_data",
    )
    restrict_number_package = fields.Boolean(
        compute="_compute_picking_type_data",
    )
    number_of_packages = fields.Integer(
        copy=False,
    )

    picking_type_id = fields.Many2one(required=True)

    picking_type_ids = fields.Many2many(
        "stock.picking.type",
        # related='picking_type_id.voucher_required',
        compute="_compute_picking_type_data",
    )
    vouchers = fields.Char(
        related="picking_ids.vouchers",
    )

    picking_count = fields.Integer(
        string="# Transferencias",
        compute="_compute_picking_count",
    )

    notes = fields.Text(help="free form remarks")

    def _compute_picking_count(self):
        """Calculate number of pickings."""
        groups = self.env["stock.picking"]._read_group(
            domain=[("batch_id", "in", self.ids)],
            groupby=["batch_id"],
            aggregates=["__count"],
        )
        counts = {g[0].id: g[1] for g in groups}
        for batch in self:
            batch.picking_count = counts.get(batch.id, 0)

    @api.depends("picking_ids")
    def _compute_picking_type_data(self):
        for rec in self:
            types = rec.picking_ids.mapped("picking_type_id")
            rec.picking_type_ids = types
            rec.voucher_required = any(x.voucher_required for x in types)
            rec.restrict_number_package = False
            # este viene exigido desde la cia pero seguramente lo movamos a
            # exigir desde picking type
            # solo es requerido para outgoings
            if rec.picking_type_code == "outgoing":
                rec.restrict_number_package = any(x.picking_type_id.restrict_number_package for x in rec.picking_ids)

    @api.onchange("picking_type_code", "partner_id")
    def changes_set_pickings(self):
        # if we change type or partner reset pickings
        self.picking_ids = False

    @api.onchange("voucher_number", "picking_ids")
    def format_voucher_number(self):
        for rec in self:
            if not rec.voucher_number:
                continue
            voucher_number = self.env["stock.picking.voucher"]._format_document_number(rec.voucher_number)
            if voucher_number and voucher_number != rec.voucher_number:
                rec.voucher_number = voucher_number

    def write(self, vals):
        if "voucher_number" in vals and vals.get("voucher_number"):
            voucher_number = self.env["stock.picking.voucher"]._format_document_number(vals.get("voucher_number"))
            if voucher_number and voucher_number != vals.get("voucher_number"):
                vals["voucher_number"] = voucher_number
        return super().write(vals)

    def action_confirm(self):
        batches_in_draft = self.filtered(lambda batch: batch.state == "draft")
        res = super().action_confirm()
        # When the batch is confirmed for the first time, Odoo already created
        # the operation lines from the selected pickings. For receptions we reset
        # them to zero so the operator can input only the quantities physically
        # received (partial reception). This must NOT touch deliveries/waves,
        # where zeroing the quantity wrongly removes product availability.
        batches_in_draft.move_line_ids.filtered(
            lambda line: line.state not in ("done", "cancel") and line.picking_id.picking_type_id.code == "incoming"
        ).write({"quantity": 0})
        return res

    def add_picking_operation(self):
        self.ensure_one()
        view_id = self.env.ref("stock_batch_picking_ux.view_move_line_tree_smart_button").id
        search_view_id = self.env.ref("stock_batch_picking_ux.stock_move_line_view_search").id
        return {
            "type": "ir.actions.act_window",
            "res_model": "stock.move.line",
            "search_view_id": search_view_id,
            "views": [[view_id, "list"], [False, "form"]],
            "domain": [["id", "in", self.move_line_ids.ids]],
            "context": {
                "create": False,
                "from_batch": True,
            },
        }

    def action_done(self):
        for rec in self:
            # al agregar la restriccion de que al menos una tenga que tener
            # cantidad entonces nunca se manda el force_qty al picking
            if all(operation.quantity == 0 for operation in rec.move_line_ids):
                raise UserError(_("Debe definir Cantidad Realizada en al menos una operación."))

            if rec.restrict_number_package and not rec.number_of_packages > 0:
                raise UserError(_("The number of packages can not be 0"))

            if rec.picking_type_id.book_required:
                if rec.picking_type_id.book_id:
                    pickings_without_book = rec.picking_ids.filtered(lambda p: not p.book_id)
                    pickings_without_book.book_id = rec.picking_type_id.book_id
                else:
                    pickings_without_book = rec.picking_ids.filtered(lambda p: not p.book_id)
                    if pickings_without_book:
                        raise UserError(
                            _("Please complete the vouchers book for the following pickings: %s")
                            % ", ".join(pickings_without_book.mapped("name"))
                        )

            if rec.number_of_packages:
                rec.picking_ids.write({"number_of_packages": rec.number_of_packages})

        # los remitos se numeran después de validar y sólo para los traslados
        # que quedaron en "done" y todavía sin remito
        res = super(StockPickingBatch, self.with_context(do_not_assign_numbers=True)).action_done()

        batch_voucher_installed = "stock_batch_picking_voucher" in self.env["ir.module.module"].search(
            [("name", "=", "stock_batch_picking_voucher"), ("state", "=", "installed")]
        ).mapped("name")

        for rec in self:
            # la rama incoming la estampa stock.picking._action_done, que además alcanza
            # la validación diferida por el wizard de orden parcial
            if rec.picking_type_code == "incoming" and rec.voucher_number:
                continue
            elif not batch_voucher_installed:
                for picking in rec.picking_ids:
                    if picking.state != "done" or picking.voucher_ids:
                        continue
                    if not picking.picking_type_id.auto_print_delivery_slip:
                        continue
                    book = picking.book_id or picking.picking_type_id.book_id
                    if not book:
                        continue
                    if all(operation.quantity == 0 for operation in picking.move_line_ids):
                        continue
                    picking.assign_numbers(picking.get_estimated_number_of_pages(), book)
        return res

    def action_view_stock_picking(self):
        """This function returns an action that display existing pickings of
        given batch picking.
        """
        self.ensure_one()
        pickings = self.mapped("picking_ids")
        action = self.env.ref("stock.action_picking_tree_all").read([])[0]
        action["domain"] = [("id", "in", pickings.ids)]
        return action
