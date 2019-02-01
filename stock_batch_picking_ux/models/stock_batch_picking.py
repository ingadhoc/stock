##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockBatchPicking(models.Model):

    _inherit = 'stock.batch.picking'

    # operation_type = fields.Selection([
    #     ('incoming', 'Suppliers'),
    #     ('outgoing', 'Customers'),
    #     ('internal', 'Internal')],
    #     'Type of Operation',
    #     required=True,
    # )
    # preferimos limitar por picking type para no confundir a los usuarios
    # porque si no podrian imaginar que al seleccionar recepciones de distintos
    # lugares van a estar recibiendo todo en una misma
    picking_code = fields.Selection([
        ('incoming', 'Suppliers'),
        ('outgoing', 'Customers'),
        ('internal', 'Internal'),
    ],
        'Type of Operation',
        # related='picking_type_id.code',
        # readonly=True,
        required=True,
        # el default sobre todo para que no necesitemos script de migracion
        default='incoming',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
    )
    # picking_type_id = fields.Many2one(
    #     'stock.picking.type',
    #     'Picking Type',
    #    states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
    #     required=True,
    # )
    partner_id = fields.Many2one(
        'res.partner',
        # por ahora lo hacemos requerido porque si no tenemos que hacer algun
        # maneje en la vista para que si esta seteado pase dominio
        # y si no esta seteado no
        # required=True,
        help='If you choose a partner then only pickings of this partner will'
        'be sellectable',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}
    )
    voucher_number = fields.Char(
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
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
    picking_type_ids = fields.Many2many(
        'stock.picking.type',
        # related='picking_type_id.voucher_required',
        compute='_compute_picking_type_data',
    )
    vouchers = fields.Char(
        related='picking_ids.vouchers',
        readonly=True,
    )
    # do this because if not allow to set the qty_done value in sml in
    #  the tree view
    move_line_ids = fields.One2many(
        'stock.move.line',
        inverse='_inverse_move_line_ids'
    )

    def _inverse_move_line_ids(self):
        pass

    # overwrite this because we need only takes the moves with are not cancel
    @api.depends('picking_ids')
    def _compute_move_lines(self):
        for batch in self:
            batch.move_lines = batch.picking_ids.mapped(
                "move_lines").filtered(lambda x: x.state != 'cancel')

    @api.depends('picking_ids')
    def _compute_picking_type_data(self):
        for rec in self:
            types = rec.picking_ids.mapped('picking_type_id')
            rec.picking_type_ids = types
            rec.voucher_required = any(x.voucher_required for x in types)
            # este viene exigido desde la cia pero seguramente lo movamos a
            # exigir desde picking type
            # solo es requerido para outgoings
            if rec.picking_code == 'outgoing':
                rec.restrict_number_package = any(
                    x.restrict_number_package for x in rec.picking_ids)
    # TODO deberiamos ver como hacer para aceptar multiples numeros de remitos
    # si llega a ser necesario
    # voucher_ids = fields.One2many(
    #     'stock.picking.voucher',
    #     'batch_picking_id',
    #     'Vouchers',
    #     copy=False
    # )
    # vouchers = fields.Char(
    #     compute='_compute_vouchers'
    # )

    # @api.multi
    # @api.depends('voucher_ids.display_name')
    # def _compute_vouchers(self):
    #     for rec in self:
    #         rec.vouchers = ', '.join(rec.mapped('voucher_ids.display_name'))

    # @api.onchange('picking_type_id', 'partner_id')
    @api.onchange('picking_code', 'partner_id')
    def changes_set_pickings(self):
        # if we change type or partner reset pickings
        self.picking_ids = False

    # @api.constrains('voucher_number', 'picking_type_id')
    @api.onchange('voucher_number', 'picking_ids')
    @api.constrains('voucher_number', 'picking_ids')
    def format_voucher_number(self):
        for rec in self:
            # TODO, mejorarlo, por ahora tomamos un solo validador
            validators = rec.picking_type_ids.mapped(
                'voucher_number_validator_id')
            if not validators:
                continue
            voucher_number = validators[0].validate_value(
                rec.voucher_number)
            if voucher_number and voucher_number != rec.voucher_number:
                rec.voucher_number = voucher_number

    @api.multi
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

    @api.multi
    def action_transfer(self):
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

            if rec.picking_code == 'incoming' and rec.voucher_number:
                for picking in rec.active_picking_ids:
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
            elif rec.picking_code != 'incoming':
                # llamamos al chequeo de stock voucher ya que este metodo
                # termina usando do_transfer pero el chequeo se llama solo
                # con do_new_transfer
                rec.active_picking_ids.do_stock_voucher_transfer_check()

        res = super(StockBatchPicking, self.with_context(
            do_not_assign_numbers=True)).action_transfer()
        # nosotros preferimos que no se haga en muchos pasos y una vez
        # confirmado se borre lo no hecho y se marque como realizado
        # lo hago para distinto de incomring porque venia andando bien para
        # Incoming, pero no debería hacer falta este chequeo
        self.remove_undone_pickings()
        return res
