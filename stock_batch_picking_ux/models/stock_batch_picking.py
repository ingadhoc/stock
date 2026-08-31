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
    # Ayuda de UI: los traslados elegibles acotados al cliente del lote. Es el
    # dominio del campo Traslados en la vista. Va aparte de allowed_picking_ids
    # a propósito: ese campo lo usa el _sanity_check nativo, así que filtrarlo
    # por cliente hacía estallar el alta de un traslado de otro cliente (o sin
    # cliente) con un mensaje que manda a revisar estado y tipo de operación,
    # que estaban perfectos — y solo por algunos caminos, según si el compute de
    # partner_id llegaba a recalcular antes (tarea 73086).
    partner_allowed_picking_ids = fields.One2many(
        "stock.picking",
        compute="_compute_partner_allowed_picking_ids",
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
            if len(partners) == 1:
                batch.partner_id = partners
            elif partners:
                # varios clientes entre los traslados: ambiguo, se limpia
                batch.partner_id = False
            else:
                # lote sin traslados: no pisar el cliente cargado a mano
                batch.partner_id = batch.partner_id

    @api.depends("partner_id", "allowed_picking_ids")
    def _compute_partner_allowed_picking_ids(self):
        for rec in self:
            pickings = rec.allowed_picking_ids
            if rec.partner_id:
                pickings = pickings.filtered(lambda p: p.partner_id == rec.partner_id)
            rec.partner_allowed_picking_ids = pickings

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
        """Al fijar/cambiar el cliente sacamos del lote solo los traslados que no
        son de ese cliente (antes vaciaba todo, lo que se peleaba con el compute
        de partner_id y dejaba el campo inutilizable en un lote nuevo). Con cliente
        vacío se mantienen los traslados. El tipo de operación lo protege un
        constraint de Odoo, no hace falta disparar onchange."""
        for rec in self.filtered("partner_id"):
            rec.picking_ids = rec.picking_ids.filtered(lambda p: p.partner_id == rec.partner_id)

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
