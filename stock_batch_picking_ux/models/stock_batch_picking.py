##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"

    picking_type_code = fields.Selection(store=True)
    partner_id = fields.Many2one(
        "res.partner",
        compute="_compute_partner_id",
        store=True,
        readonly=False,
        help=(
            "Computed from the pickings in the batch: set automatically when all "
            "pickings share the same partner; cleared when there are multiple. "
            "Editable manually until the batch is done."
        ),
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
        compute="_compute_picking_type_data",
    )
    picking_count = fields.Integer(
        string="# Transferencias",
        compute="_compute_picking_count",
    )
    notes = fields.Text(help="free form remarks")

    # Stub to prevent AttributeError when l10n_pe_edi_stock is installed.
    # PE adds a non-primary inheritance on stock.report_delivery_document with
    # a t-if block guarded by o.l10n_pe_edi_status. Our batch primary template
    # inherits the parent's combined arch and the PE block lands inside; at
    # render time `o` is a stock.picking.batch (no such field) and Qweb raises.
    # Exposing the field with a False value at the batch level short-circuits
    # the t-if cleanly without needing a bridge module.
    l10n_pe_edi_status = fields.Char(default=False, store=False, readonly=True)

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

    @api.depends("picking_ids.partner_id")
    def _compute_partner_id(self):
        for batch in self:
            partners = batch.picking_ids.mapped("partner_id")
            batch.partner_id = partners if len(partners) == 1 else False

    @api.depends("partner_id")
    def _compute_allowed_picking_ids(self):
        super()._compute_allowed_picking_ids()
        for rec in self.filtered("partner_id"):
            rec.allowed_picking_ids = rec.allowed_picking_ids.filtered(lambda p: p.partner_id == rec.partner_id)

    def write(self, vals):
        # Intercept DELETE commands on picking_ids to prevent physical deletion —
        # removing from the batch (UNLINK) is sufficient.
        if "picking_ids" in vals:
            vals["picking_ids"] = [
                Command.unlink(op[1]) if op[0] == Command.DELETE else op for op in vals["picking_ids"]
            ]
        return super().write(vals)

    @api.depends("picking_ids")
    def _compute_picking_type_data(self):
        for rec in self:
            types = rec.picking_ids.mapped("picking_type_id")
            rec.picking_type_ids = types
            rec.restrict_number_package = False
            # solo es requerido para outgoings
            if rec.picking_type_code == "outgoing":
                rec.restrict_number_package = any(t.restrict_number_package for t in types)

    @api.onchange("partner_id")
    def changes_set_pickings(self):
<<<<<<< 8b1493de9906b9f991195e66de149c8aa7f66608
        """we reset pickings if partner_id is changed and set, if partner is empty we keep previous pickings.
        Operation type is protected by odoo (without onchange, by a constraint), no need to trigger onchange"""
        for rec in self.filtered("partner_id"):
            rec.picking_ids = False
||||||| 5c4c4f22e4695c1a7871d31b873b66b0e893cf18
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
        # the operation lines from the selected pickings. We reset them to zero
        # so the operator can input only the quantities that will actually be processed.
        batches_in_draft.move_line_ids.filtered(lambda line: line.state not in ("done", "cancel")).write(
            {"quantity": 0}
        )
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
=======
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
>>>>>>> e8b8a7009dcdf451dfe9edf66870269aef808a28

    def action_done(self):
        for rec in self:
            if rec.restrict_number_package and not rec.number_of_packages > 0:
                raise UserError(_("The number of packages can not be 0"))
            if rec.number_of_packages:
                rec.picking_ids.write({"number_of_packages": rec.number_of_packages})
        return super().action_done()

    def action_print_delivery_slip(self):
        """Choose between consolidated batch report and per-picking individual
        delivery slips depending on whether the batch has a partner.

        Batch with partner → consolidated (all transfers share one customer,
        one delivery slip). Batch without partner → individual slips, one per
        picking (mixed-partner batch handles delivery guides at picking level).
        """
        self.ensure_one()
        if self.partner_id:
            return self.env.ref("stock_batch_picking_ux.action_report_batch_deliveryslip").report_action(self)
        return self.env.ref("stock.action_report_delivery").report_action(self.picking_ids)

    def action_view_stock_picking(self):
        """This function returns an action that display existing pickings of
        given batch picking.
        """
        self.ensure_one()
        pickings = self.mapped("picking_ids")
        action = self.env.ref("stock.action_picking_tree_all").read([])[0]
        action["domain"] = [("id", "in", pickings.ids)]
        return action
