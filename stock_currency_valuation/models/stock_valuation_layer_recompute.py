from odoo import Command, api, fields, models
from odoo.addons.account.models.account_move_line import AccountMoveLine
from odoo.exceptions import UserError


def patch_check_reconciliation(self):
    return
class StockValuationLayerRecompute(models.Model):

    _name = 'stock.valuation.layer.recompute'
    _description = "layer recompute"


    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        readonly=False
    )
    valuation_currency_id = fields.Many2one(
        'res.currency',
        string='Secondary Currency Valuation',
        compute="_compute_valuation_currency_id"
    )
    initial_amount = fields.Monetary()
    final_amount = fields.Monetary()
    initial_amount_in_currency = fields.Monetary()
    final_amount_in_currency = fields.Monetary()
    line_ids = fields.One2many(
        comodel_name='stock.valuation.layer.recompute.line',
        inverse_name='recompute_id',
    )
    last_manual_svl_id = fields.Many2one('stock.valuation.layer')
    amount_changed = fields.Boolean()
    slv_changed = fields.Boolean()

    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_process', 'In Process'),
        ('done', 'Done'),
        ('no_change', 'Not changes Required'),
        ('cancel', 'Cancelled')
    ], default='draft', string='Status', required=True, readonly=True, copy=False)

    @api.onchange('product_id', 'company_id')
    def _onchange_product_id(self):
        self.line_ids = False
        self.final_amount_in_currency = False

    @api.depends('product_id', 'company_id')
    def _compute_valuation_currency_id(self):
        for rec in self:
            product_id = rec.product_id.with_company(rec.company_id)
            rec.valuation_currency_id = product_id.categ_id.valuation_currency_id

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'

    def back_to_draft(self):
        for rec in self:
            rec.state = 'draft'

    def delete_adjust_compute_lines(self):
        self.env['stock.valuation.layer'].search(
            [('company_id', '=', self.company_id.id), ('product_id', '=', self.product_id.id), ('description', 'ilike', 'manual%')]
            , order="create_date desc").sudo().unlink()
        self.action_compute_lines()

    def action_compute_lines(self):

        # last_manual_svl_id = self.env['stock.valuation.layer'].search(
        #     [('company_id', '=', self.company_id.id), ('product_id', '=', self.product_id.id), ('description', 'ilike', 'manual%')]
        #     , order="create_date desc", limit=1)
        # self.last_manual_svl_id = last_manual_svl_id

        self.last_manual_svl_id = False
        leaf = [('company_id', '=', self.company_id.id), ('product_id', '=', self.product_id.id)]
        svl_ids = self.env['stock.valuation.layer'].search(leaf, order="create_date asc")
        lines = [Command.clear()]
        quantity_at_time = 0
        standard_price_in_currency = 0
        standard_price = 0

        self.initial_amount_in_currency = self.product_id.with_company(self.company_id.id).standard_price_in_currency
        self.initial_amount = self.product_id.with_company(self.company_id.id).standard_price
        for svl_id in svl_ids:
            svl_type = ''
            vals = {
                'layer_id': svl_id.id,
                'layer_unit_cost': svl_id.unit_cost,
                'layer_value': svl_id.value,
                'layer_unit_cost_in_currency': svl_id.unit_cost_in_currency,
                'layer_value_in_currency': svl_id.value_in_currency,
            }
            quantity_at_time = quantity_at_time + svl_id.quantity

            if svl_id.stock_move_id and (svl_id.stock_move_id._is_out() or svl_id.stock_move_id.is_inventory):
                # Si el movimento es de salida o de inventario, valor es el registrado en el producto
                standard_price_in_currency = standard_price_in_currency if standard_price_in_currency else  svl_id.unit_cost_in_currency
                standard_price = standard_price if standard_price else  svl_id.unit_cost

                new_unit_cost = standard_price
                new_value = standard_price * svl_id.quantity

                new_unit_cost_in_currency = standard_price_in_currency
                new_value_in_currency = standard_price_in_currency * svl_id.quantity

                svl_type = 'inventory' if svl_id.stock_move_id.is_inventory else 'out'

            # es un ajuste?
            #elif svl_id.description.startswith('Valor del producto modificado') or svl_id.description.startswith('Manual'):
            elif not svl_id.stock_move_id:
                new_value_in_currency = svl_id.value_in_currency
                new_unit_cost_in_currency = svl_id.unit_cost_in_currency
                standard_price_in_currency = (new_value_in_currency + standard_price_in_currency * (quantity_at_time - svl_id.quantity)) / quantity_at_time if quantity_at_time else standard_price_in_currency

                new_value = svl_id.value
                new_unit_cost = svl_id.unit_cost
                standard_price = (new_value + standard_price * (quantity_at_time - svl_id.quantity)) / quantity_at_time if quantity_at_time else standard_price

                svl_type = 'ajustement'

            elif svl_id.stock_move_id and svl_id.stock_move_id._is_returned(valued_type='in'):
                # Si es una devolucion y existe el movimiento de origen
                # el valor de avco sale del mov de origen sino sale de producto

                if svl_id.stock_move_id.origin_returned_move_id:
                    for temp_vals in lines:
                        if temp_vals[2] and  temp_vals[2]['layer_id'] in svl_id.stock_move_id.origin_returned_move_id.stock_valuation_layer_ids.ids:
                            new_value_in_currency = temp_vals[2]['new_unit_cost_in_currency'] * svl_id.quantity
                            new_unit_cost_in_currency = temp_vals[2]['new_unit_cost_in_currency']
                            standard_price_in_currency = (new_value_in_currency + standard_price_in_currency * (quantity_at_time - svl_id.quantity)) / quantity_at_time if quantity_at_time else standard_price_in_currency
                            new_value = temp_vals[2]['new_unit_cost'] * svl_id.quantity
                            new_unit_cost = temp_vals[2]['new_unit_cost']
                            standard_price = (new_value + standard_price * (quantity_at_time - svl_id.quantity)) / quantity_at_time if quantity_at_time else standard_price

                            svl_type = 'return  of  %s ' % temp_vals[2]['layer_id']

                            break
                else:
                    new_value_in_currency = standard_price_in_currency * svl_id.quantity
                    new_unit_cost_in_currency = standard_price_in_currency
                    new_value = standard_price * svl_id.quantity
                    new_unit_cost = standard_price

                    svl_type = 'ret_without_move'

            elif svl_id.manual_currency_rate:
                # caso viene de un landed cost con manual currency rate
                if svl_id.stock_landed_cost_id.inverse_currency_rate:

                    new_value = svl_id.value
                    new_unit_cost = svl_id.unit_cost
                    standard_price = (new_value + standard_price * (quantity_at_time - svl_id.quantity)) / quantity_at_time if quantity_at_time else standard_price

                    new_value_in_currency = svl_id.value * svl_id.manual_currency_rate
                    new_unit_cost_in_currency = new_value_in_currency / svl_id.quantity if svl_id.quantity else 0
                    standard_price_in_currency = (new_value_in_currency + standard_price_in_currency * (quantity_at_time - svl_id.quantity)) / quantity_at_time if quantity_at_time else standard_price_in_currency

                    svl_type = 'landed manual rate %s' % svl_id.manual_currency_rate
                # caso viene de una compra con manual currency rate
                elif svl_id.stock_move_id.picking_id.currency_rate and svl_id.stock_move_id.purchase_line_id.order_id.currency_id == svl_id.stock_move_id.picking_id.valuation_currency_id:
                    price_unit = svl_id.stock_move_id.purchase_line_id.price_unit / svl_id.stock_move_id.picking_id.currency_rate

                    new_value_in_currency = svl_id.stock_move_id.purchase_line_id.price_unit * svl_id.quantity
                    new_unit_cost_in_currency = svl_id.stock_move_id.purchase_line_id.price_unit
                    standard_price_in_currency = (new_value_in_currency + standard_price_in_currency * (quantity_at_time - svl_id.quantity)) / quantity_at_time if quantity_at_time else standard_price_in_currency


                    new_value = price_unit * svl_id.quantity
                    new_unit_cost = price_unit
                    standard_price = (new_value + standard_price * (quantity_at_time - svl_id.quantity)) / quantity_at_time if quantity_at_time else standard_price
                # Otros casos ?
                    svl_type = 'purchase manual rate %s' % svl_id.manual_currency_rate
                else:
                    new_value = svl_id.value
                    new_unit_cost = svl_id.unit_cost
                    standard_price = (new_value + standard_price * (quantity_at_time - svl_id.quantity)) / quantity_at_time if quantity_at_time else standard_price

                    new_value_in_currency = svl_id.value * svl_id.manual_currency_rate
                    new_unit_cost_in_currency = new_value_in_currency / svl_id.quantity if svl_id.quantity else 0
                    standard_price_in_currency = (new_value_in_currency + standard_price_in_currency * (quantity_at_time - svl_id.quantity)) / quantity_at_time if quantity_at_time else standard_price_in_currency

                    svl_type = 'manual currency rate %s' % svl_id.manual_currency_rate
            else:
                if svl_id.stock_landed_cost_id.valuation_currency_id:
                    new_value_in_currency = svl_id.currency_id._convert(
                        from_amount=svl_id.value,
                        to_currency=svl_id.valuation_currency_id,
                        company=svl_id.company_id,
                        date=svl_id.create_date,
                    )
                    new_value = svl_id.value
                    new_unit_cost = svl_id.unit_cost
                    standard_price = (new_value + standard_price * (quantity_at_time - svl_id.quantity)) / quantity_at_time if quantity_at_time else standard_price

                    new_unit_cost_in_currency = new_value_in_currency / svl_id.quantity if svl_id.quantity else 0
                    standard_price_in_currency = (new_value_in_currency + standard_price_in_currency * (quantity_at_time - svl_id.quantity)) / quantity_at_time if quantity_at_time else standard_price_in_currency
                    svl_type = 'slv'

                elif svl_id.stock_move_id.picking_id.valuation_currency_id and svl_id.stock_move_id.purchase_line_id.order_id.currency_id == svl_id.stock_move_id.picking_id.valuation_currency_id:

                    new_value = svl_id.valuation_currency_id._convert(
                        from_amount=svl_id.value_in_currency,
                        to_currency=svl_id.currency_id,
                        company=svl_id.company_id,
                        date=svl_id.create_date,
                    )

                    new_value_in_currency = svl_id.stock_move_id.purchase_line_id.price_unit * svl_id.quantity
                    new_unit_cost_in_currency = svl_id.stock_move_id.purchase_line_id.price_unit
                    standard_price_in_currency = (new_value_in_currency + standard_price_in_currency * (quantity_at_time - svl_id.quantity)) / quantity_at_time if quantity_at_time else standard_price_in_currency


                    new_value = new_value
                    new_unit_cost = new_value / svl_id.quantity if svl_id.quantity else 0
                    standard_price = (new_value + standard_price * (quantity_at_time - svl_id.quantity)) / quantity_at_time if quantity_at_time else standard_price
                    svl_type = 'slv'
                else:
                    new_value_in_currency = svl_id.currency_id._convert(
                        from_amount=svl_id.value,
                        to_currency=svl_id.valuation_currency_id,
                        company=svl_id.company_id,
                        date=svl_id.create_date,
                    )
                    new_value = svl_id.value
                    new_unit_cost = svl_id.unit_cost
                    standard_price = (new_value + standard_price * (quantity_at_time - svl_id.quantity)) / quantity_at_time if quantity_at_time else standard_price

                    new_unit_cost_in_currency = new_value_in_currency / svl_id.quantity if svl_id.quantity else 0
                    standard_price_in_currency = (new_value_in_currency + standard_price_in_currency * (quantity_at_time - svl_id.quantity)) / quantity_at_time if quantity_at_time else standard_price_in_currency
                    svl_type = 'slv'

            if quantity_at_time == 0:
                standard_price_in_currency = 0
                standard_price = 0

            vals['new_value'] = new_value
            vals['new_unit_cost'] = new_unit_cost
            vals['standard_price'] = standard_price

            vals['new_value_in_currency'] = new_value_in_currency
            vals['new_unit_cost_in_currency'] = new_unit_cost_in_currency
            vals['standard_price_in_currency'] = standard_price_in_currency
            vals['quantity_at_time'] = quantity_at_time
            vals['svl_type'] = svl_type

            need_change_1 = self.valuation_currency_id.compare_amounts(svl_id.value_in_currency, new_value_in_currency) != 0.0
            need_change_2 = self.valuation_currency_id.compare_amounts(svl_id.unit_cost_in_currency, new_unit_cost_in_currency) != 0.0
            need_change_3 = self.currency_id.compare_amounts(svl_id.value, new_value) != 0.0
            need_change_4 = self.currency_id.compare_amounts(svl_id.unit_cost, new_unit_cost) != 0.0

            #need_change_5 = svl_id.id > last_manual_svl_id.id or not last_manual_svl_id
            need_change_5 = True
            vals['need_changes'] = True if (need_change_1 or need_change_2 or need_change_3 or need_change_4) and need_change_5 else False
            lines.append(Command.create(vals),)
        self.line_ids = lines
        self.final_amount_in_currency = standard_price_in_currency
        self.final_amount = standard_price
        self.state = 'in_process'
        self.action_check_need_changes()

    def action_check_need_changes(self):
        if not self.line_ids.filtered('need_changes') and \
            self.final_amount_in_currency == self.initial_amount_in_currency or \
            self.final_amount == self.initial_amount:
            self.state = 'no_change'

    def action_manual_slv_revaluation(self):
        orig_check_reconciliation = AccountMoveLine._check_reconciliation
        AccountMoveLine._check_reconciliation = patch_check_reconciliation
        slv_changed = False

        for line_id in self.line_ids.filtered('need_changes'):
            slv_changed = True
            if line_id.layer_id.stock_landed_cost_id:
                raise UserError('No puedo ajustar un landed cost')
            line_id.layer_id.write({
                'unit_cost_in_currency': line_id.new_unit_cost_in_currency,
                'value_in_currency':line_id.new_value_in_currency,
                'unit_cost': line_id.new_unit_cost_in_currency,
                'value':line_id.new_value_in_currency
            })
            lines = []
            for move_line in  line_id.layer_id.account_move_id.line_ids.filtered(lambda x: x.product_id == self.product_id):
                multiplier = 1 if move_line.amount_currency >= 0 else -1
                field = 'debit' if move_line.credit == 0 else 'credit'
                lines.append(Command.update(move_line.id,{
                    'amount_currency': line_id.new_value_in_currency * multiplier,
                    field: line_id.new_value,
                }))
            if lines:
                line_id.layer_id.account_move_id.line_ids = lines

        if self.product_id.with_company(self.company_id.id).standard_price_in_currency != self.final_amount_in_currency:
            self.product_id.with_company(self.company_id.id).with_context(
                disable_auto_svl=True
                ).sudo().write({'standard_price_in_currency': self.final_amount_in_currency})
            self.amount_changed = True
        if self.product_id.with_company(self.company_id.id).standard_price != self.final_amount:
            self.product_id.with_company(self.company_id.id).with_context(
                disable_auto_svl=True
                ).sudo().write({'standard_price': self.final_amount})
            self.amount_changed = True

        self.slv_changed = slv_changed
        AccountMoveLine._check_reconciliation = orig_check_reconciliation
        self.state = 'done'


class StockValuationLayerRecomputeLine(models.Model):

    _name = 'stock.valuation.layer.recompute.line'
    _description = "lines layer recompute"


    layer_id = fields.Many2one('stock.valuation.layer')
    quantity = fields.Float(related="layer_id.quantity")
    quantity_at_time = fields.Float()
    layer_date = fields.Datetime(related="layer_id.create_date")
    recompute_id = fields.Many2one('stock.valuation.layer.recompute')
    currency_id = fields.Many2one('res.currency', related='recompute_id.valuation_currency_id')
    company_currency_id = fields.Many2one('res.currency', related='recompute_id.currency_id')

    # company currency
    layer_unit_cost = fields.Monetary(currency_field="company_currency_id")
    layer_value = fields.Monetary(currency_field="company_currency_id")
    new_unit_cost = fields.Monetary(currency_field="company_currency_id")
    new_value = fields.Monetary(currency_field="company_currency_id")
    standard_price = fields.Monetary(currency_field="company_currency_id")

    # Secundary currency
    layer_unit_cost_in_currency = fields.Monetary()
    layer_value_in_currency = fields.Monetary()
    new_unit_cost_in_currency = fields.Monetary()
    new_value_in_currency = fields.Monetary()
    standard_price_in_currency = fields.Monetary()
    need_changes = fields.Boolean()
    svl_type = fields.Char()
