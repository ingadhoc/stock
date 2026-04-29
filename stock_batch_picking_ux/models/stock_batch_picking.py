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

    @api.depends("partner_id")
    def _compute_allowed_picking_ids(self):
        super()._compute_allowed_picking_ids()
        for rec in self.filtered("partner_id"):
            rec.allowed_picking_ids = rec.allowed_picking_ids.filtered(lambda p: p.partner_id == rec.partner_id)

    def write(self, vals):
        # Interceptamos las operaciones de picking_ids para evitar que se borren físicamente
        # En lugar de comando 2 (delete), usamos comando 3 (unlink) que solo desvincula
        if "picking_ids" in vals:
            new_picking_ops = []
            for operation in vals["picking_ids"]:
                if operation[0] == 2:  # Si es un delete (2), lo convertimos a unlink (3)
                    new_picking_ops.append((3, operation[1]))  # Unlink en lugar de delete
                else:
                    new_picking_ops.append(operation)
            vals["picking_ids"] = new_picking_ops
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

    @api.onchange("picking_type_code", "partner_id")
    def changes_set_pickings(self):
        # if we change type or partner reset pickings
        self.picking_ids = False

    def action_done(self):
        for rec in self:
            if rec.restrict_number_package and not rec.number_of_packages > 0:
                raise UserError(_("The number of packages can not be 0"))
            if rec.number_of_packages:
                rec.picking_ids.write({"number_of_packages": rec.number_of_packages})
        return super().action_done()

    def action_view_stock_picking(self):
        """This function returns an action that display existing pickings of
        given batch picking.
        """
        self.ensure_one()
        pickings = self.mapped("picking_ids")
        action = self.env.ref("stock.action_picking_tree_all").read([])[0]
        action["domain"] = [("id", "in", pickings.ids)]
        return action
