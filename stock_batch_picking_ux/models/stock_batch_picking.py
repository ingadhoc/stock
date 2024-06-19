##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockPickingBatch(models.Model):

    _inherit = 'stock.picking.batch'

    picking_type_code = fields.Selection(store=True)
    partner_id = fields.Many2one(
        'res.partner',
        # por ahora lo hacemos requerido porque si no tenemos que hacer algun
        # maneje en la vista para que si esta seteado pase dominio
        # y si no esta seteado no
        # required=True,
        help='If you choose a partner then only pickings of this partner will'
        'be sellectable',
    )
    voucher_number = fields.Char(
    )
    voucher_required = fields.Boolean(
        # related='picking_type_id.voucher_required',
        compute='_compute_picking_type_data',
    )
    restrict_number_package = fields.Boolean(
        compute='_compute_picking_type_data',
    )
    number_of_packages = fields.Integer(
        copy=False,
    )

    picking_type_id = fields.Many2one(required=True)

    picking_type_ids = fields.Many2many(
        'stock.picking.type',
        # related='picking_type_id.voucher_required',
        compute='_compute_picking_type_data',
    )
    vouchers = fields.Char(
        related='picking_ids.vouchers',
    )

    picking_count = fields.Integer(
        string="# Transferencias", compute="_compute_picking_count",
    )

    notes = fields.Text(help="free form remarks")

    def _compute_picking_count(self):
        """Calculate number of pickings."""
        groups = self.env["stock.picking"]._read_group(
            domain=[("batch_id", "in", self.ids)],
            groupby=['batch_id'],
            aggregates=['__count'],
        )
        counts = {g[0].id: g[1] for g in groups}
        for batch in self:
            batch.picking_count = counts.get(batch.id, 0)

    @api.depends('picking_ids')
    def _compute_picking_type_data(self):
        for rec in self:
            types = rec.picking_ids.mapped('picking_type_id')
            rec.picking_type_ids = types
            rec.voucher_required = any(x.voucher_required for x in types)
            rec.restrict_number_package = False
            # este viene exigido desde la cia pero seguramente lo movamos a
            # exigir desde picking type
            # solo es requerido para outgoings
            if rec.picking_type_code == 'outgoing':
                rec.restrict_number_package = any(
                    x.picking_type_id.restrict_number_package
                    for x in rec.picking_ids)

    @api.onchange('picking_type_code', 'partner_id')
    def changes_set_pickings(self):
        # if we change type or partner reset pickings
        self.picking_ids = False

    @api.onchange('voucher_number', 'picking_ids')
    def format_voucher_number(self):
        for rec in self:
            if not rec.voucher_number:
                continue
            voucher_number = self.env['stock.picking.voucher']._format_document_number(rec.voucher_number)
            if voucher_number and voucher_number != rec.voucher_number:
                rec.voucher_number = voucher_number

    def write(self, vals):
        if 'voucher_number' in vals and vals.get('voucher_number'):
            voucher_number = self.env['stock.picking.voucher']._format_document_number(vals.get('voucher_number'))
            if voucher_number and voucher_number != vals.get('voucher_number'):
                vals['voucher_number'] = voucher_number
        return super().write(vals)

    def add_picking_operation(self):
        self.ensure_one()
        view_id = self.env.ref('stock_ux.view_move_line_tree').id
        search_view_id = self.env.ref(
            'stock_ux.stock_move_line_view_search').id
        return {
            "type": "ir.actions.act_window",
            "res_model": "stock.move.line",
            "search_view_id": search_view_id,
            "views": [[view_id, "tree"], [False, "form"]],
            "domain": [["id", "in", self.move_line_ids.ids]],
            "context": {"create": False, "from_batch": True},
        }

    def action_done(self):
        # agregamos los numeros de remito
        for rec in self:
            # al agregar la restriccion de que al menos una tenga que tener
            # cantidad entonces nunca se manda el force_qty al picking
            if all(operation.qty_done == 0
                    for operation in rec.move_line_ids):
                raise UserError(_(
                    'Debe definir Cantidad Realizada en al menos una '
                    'operación.'))

            if rec.restrict_number_package and not rec.number_of_packages > 0:
                raise UserError(_('The number of packages can not be 0'))
            if rec.number_of_packages:
                rec.picking_ids.write({
                    'number_of_packages': rec.number_of_packages})

            if rec.picking_type_code == 'incoming' and rec.voucher_number:
                for picking in rec.picking_ids:
                    # agregamos esto para que no se asigne a los pickings
                    # que no se van a recibir ya que todavia no se limpiaron
                    # y ademas, por lo de arriba, no se fuerza la cantidad
                    # si son todos cero, se terminan sacando
                    if all(operation.qty_done == 0
                            for operation in picking.move_line_ids):
                        continue
                    rec.env['stock.picking.voucher'].create({
                        'picking_id': picking.id,
                        'name': rec.voucher_number,
                    })

        return super(StockPickingBatch, self.with_context(do_not_assign_numbers=True)).action_done()

    def action_view_stock_picking(self):
        """This function returns an action that display existing pickings of
        given batch picking.
        """
        self.ensure_one()
        pickings = self.mapped("picking_ids")
        action = self.env.ref("stock.action_picking_tree_all").read([])[0]
        action["domain"] = [("id", "in", pickings.ids)]
        return action
