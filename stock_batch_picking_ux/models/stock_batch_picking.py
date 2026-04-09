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
        # por ahora lo hacemos requerido porque si no tenemos que hacer algun
        # maneje en la vista para que si esta seteado pase dominio
        # y si no esta seteado no
        # required=True,
<<<<<<< 0c1847d1a8ee87c8f1ec5de54e3f0fc340dce82d
        help="If you choose a partner then only pickings of this partner will be selectable",
||||||| 1e7ca838e726003d0cd731475a7fc033d8348655
        help="If you choose a partner then only pickings of this partner will" "be sellectable",
    )
    voucher_number = fields.Char()
    voucher_required = fields.Boolean(
        # related='picking_type_id.voucher_required',
        compute="_compute_picking_type_data",
=======
        help="If you choose a partner then only pickings of this partner will be sellectable",
    )
    voucher_number = fields.Char()
    voucher_required = fields.Boolean(
        # related='picking_type_id.voucher_required',
        compute="_compute_picking_type_data",
>>>>>>> dcea2b2310a8fb7db8f4388ea08dad92a209d57b
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

    @api.onchange("picking_type_code", "partner_id")
    def changes_set_pickings(self):
        # if we change type or partner reset pickings
        self.picking_ids = False

    def action_done(self):
        for rec in self:
<<<<<<< 0c1847d1a8ee87c8f1ec5de54e3f0fc340dce82d
||||||| 1e7ca838e726003d0cd731475a7fc033d8348655
            # al agregar la restriccion de que al menos una tenga que tener
            # cantidad entonces nunca se manda el force_qty al picking
            if all(operation.quantity == 0 for operation in rec.move_line_ids):
                raise UserError(_("Debe definir Cantidad Realizada en al menos una " "operación."))

=======
            # al agregar la restriccion de que al menos una tenga que tener
            # cantidad entonces nunca se manda el force_qty al picking
            if all(operation.quantity == 0 for operation in rec.move_line_ids):
                raise UserError(_("Debe definir Cantidad Realizada en al menos una operación."))

>>>>>>> dcea2b2310a8fb7db8f4388ea08dad92a209d57b
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
<<<<<<< 0c1847d1a8ee87c8f1ec5de54e3f0fc340dce82d
        return super().action_done()
||||||| 1e7ca838e726003d0cd731475a7fc033d8348655

            if rec.picking_type_code == "incoming" and rec.voucher_number:
                for picking in rec.picking_ids:
                    # agregamos esto para que no se asigne a los pickings
                    # que no se van a recibir ya que todavia no se limpiaron
                    # y ademas, por lo de arriba, no se fuerza la cantidad
                    # si son todos cero, se terminan sacando
                    if all(operation.quantity == 0 for operation in picking.move_line_ids):
                        continue
                    rec.env["stock.picking.voucher"].create(
                        {
                            "picking_id": picking.id,
                            "name": rec.voucher_number,
                        }
                    )
        return super(StockPickingBatch, self.with_context(do_not_assign_numbers=True)).action_done()
=======

            if rec.picking_type_code == "incoming" and rec.voucher_number:
                for picking in rec.picking_ids:
                    # agregamos esto para que no se asigne a los pickings
                    # que no se van a recibir ya que todavia no se limpiaron
                    # y ademas, por lo de arriba, no se fuerza la cantidad
                    # si son todos cero, se terminan sacando
                    if all(operation.quantity == 0 for operation in picking.move_line_ids):
                        continue
                    rec.env["stock.picking.voucher"].create(
                        {
                            "picking_id": picking.id,
                            "name": rec.voucher_number,
                        }
                    )
            else:
                batch_voucher_installed = "stock_batch_picking_voucher" in self.env["ir.module.module"].search(
                    [("name", "=", "stock_batch_picking_voucher"), ("state", "=", "installed")]
                ).mapped("name")
                if not batch_voucher_installed:
                    for picking in rec.picking_ids:
                        if not picking.picking_type_id.auto_print_delivery_slip:
                            continue
                        book = picking.book_id or picking.picking_type_id.book_id
                        if not book:
                            continue
                        if all(operation.quantity == 0 for operation in picking.move_line_ids):
                            continue
                        picking.assign_numbers(picking.get_estimated_number_of_pages(), book)
        return super(StockPickingBatch, self.with_context(do_not_assign_numbers=True)).action_done()
>>>>>>> dcea2b2310a8fb7db8f4388ea08dad92a209d57b

    def action_view_stock_picking(self):
        """This function returns an action that display existing pickings of
        given batch picking.
        """
        self.ensure_one()
        pickings = self.mapped("picking_ids")
        action = self.env.ref("stock.action_picking_tree_all").read([])[0]
        action["domain"] = [("id", "in", pickings.ids)]
        return action
