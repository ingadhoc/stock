from odoo import Command, api, fields, models
from odoo.addons.account.models.account_move_line import AccountMoveLine
from odoo.exceptions import UserError


def patch_check_reconciliation(self):
    return
# Todo - agregar estado
# -1 draft solo modifico producto
# 2 in_process  cuando apreto action_compute_lines se computan las lineas y se pone es ente estado (puedoapretar mas de una vz )
# el boton action_compute_lines se ve en draft u en process
# 3  done no dear moficar
# 4 cancel
# action_manual_slv_revaluation pasa a done
# metodo que pase cancel
# vista de lista al menu
class StockValuationLayerRecompute(models.model):

    _name = 'stock.valuation.layer.recompute'
    _description = "layer recompute"


    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    product_id = fields.Many2one('product.product', string='Product')
    valuation_currency_id = fields.Many2one(
        'res.currency',
        string='Secondary Currency Valuation',
        compute="_compute_valuation_currency_id"
    )
    initial_amount_in_currency = fields.Monetary()
    final_amount_in_currency = fields.Monetary()
    line_ids = fields.One2many(
        comodel_name='stock.valuation.layer.recompute.line',
        inverse_name='recompute_id',
    )
    last_manual_svl_id = fields.Many2one('stock.valuation.layer')

    @api.onchange('product_id', 'company_id')
    def _onchange_product_id(self):
        self.line_ids = False
        self.final_amount_in_currency = False

    @api.depends('product_id', 'company_id')
    def _compute_valuation_currency_id(self):
        for rec in self:
            product_id = rec.product_id.with_company(rec.company_id)
            rec.valuation_currency_id = product_id.categ_id.valuation_currency_id

    def action_compute_lines(self):

        last_manual_svl_id = self.env['stock.valuation.layer'].search(
            [('company_id', '=', self.company_id.id), ('product_id', '=', self.product_id.id), ('description', 'ilike', 'manual%')]
            , order="create_date desc", limit=1)
        self.last_manual_svl_id = last_manual_svl_id

        leaf = [('company_id', '=', self.company_id.id), ('product_id', '=', self.product_id.id)]
        svl_ids = self.env['stock.valuation.layer'].search(leaf, order="create_date asc")
        lines = [Command.clear()]
        quantity_at_time = 0
        standard_price_in_currency = self.initial_amount_in_currency

        for svl_id in svl_ids:
            svl_type = ''
            vals = {'layer_id': svl_id.id}
            quantity_at_time = quantity_at_time + svl_id.quantity

            if svl_id.stock_move_id and (svl_id.stock_move_id._is_out() or svl_id.stock_move_id.is_inventory):
                # Si el movimento es de salida o de inventario, valor es el registrado en el producto
                standard_price_in_currency = standard_price_in_currency if standard_price_in_currency else  svl_id.unit_cost_in_currency
                new_unit_cost_in_currency = standard_price_in_currency
                new_value_in_currency = standard_price_in_currency * svl_id.quantity
                svl_type = 'inventory' if svl_id.stock_move_id.is_inventory else 'out'

            # es un ajuste?
            #elif svl_id.description.startswith('Valor del producto modificado') or svl_id.description.startswith('Manual'):
            elif not svl_id.stock_move_id:
                new_value_in_currency = svl_id.value_in_currency
                new_unit_cost_in_currency = svl_id.unit_cost_in_currency
                standard_price_in_currency = (new_value_in_currency + standard_price_in_currency * (quantity_at_time - svl_id.quantity)) / quantity_at_time if quantity_at_time else standard_price_in_currency
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
                            svl_type = 'return  of  %s ' % temp_vals[2]['layer_id']

                            break
                else:
                    new_value_in_currency = standard_price_in_currency * svl_id.quantity
                    new_unit_cost_in_currency = standard_price_in_currency
                    svl_type = 'ret_without_move'

            elif svl_id.manual_currency_rate:
                new_value_in_currency = svl_id.value * svl_id.manual_currency_rate
                new_unit_cost_in_currency = new_value_in_currency / svl_id.quantity if svl_id.quantity else 0

                standard_price_in_currency = (new_value_in_currency + standard_price_in_currency * (quantity_at_time - svl_id.quantity)) / quantity_at_time if quantity_at_time else standard_price_in_currency
                svl_type = 'manual currency rate %s' % svl_id.manual_currency_rate
            else:
                new_value_in_currency = svl_id.currency_id._convert(
                    from_amount=svl_id.value,
                    to_currency=svl_id.valuation_currency_id,
                    company=svl_id.company_id,
                    date=svl_id.create_date,
                )
                new_unit_cost_in_currency = new_value_in_currency / svl_id.quantity if svl_id.quantity else 0
                standard_price_in_currency = (new_value_in_currency + standard_price_in_currency * (quantity_at_time - svl_id.quantity)) / quantity_at_time if quantity_at_time else standard_price_in_currency
                svl_type = 'slv'

            vals['new_value_in_currency'] = new_value_in_currency
            vals['new_unit_cost_in_currency'] = new_unit_cost_in_currency
            vals['standard_price_in_currency'] = standard_price_in_currency
            vals['quantity_at_time'] = quantity_at_time
            vals['svl_type'] = svl_type

            need_change_1 = self.valuation_currency_id.compare_amounts(svl_id.value_in_currency, new_value_in_currency) != 0.0
            need_change_2 = self.valuation_currency_id.compare_amounts(svl_id.unit_cost_in_currency, new_unit_cost_in_currency) != 0.0
            need_change_3 = svl_id.id > last_manual_svl_id.id or not last_manual_svl_id
            vals['need_changes'] = True if (need_change_1 or need_change_2) and need_change_3 else False
            lines.append(Command.create(vals),)
        self.line_ids = lines
        self.final_amount_in_currency = standard_price_in_currency

    def action_manual_slv_revaluation(self):
        orig_check_reconciliation = AccountMoveLine._check_reconciliation
        AccountMoveLine._check_reconciliation = patch_check_reconciliation

        for line_id in self.line_ids.filtered('need_changes'):
            if line_id.layer_id.stock_landed_cost_id:
                raise UserError('No puedo ajustar un landed cost')
            line_id.layer_id.write({
                'unit_cost_in_currency': line_id.new_unit_cost_in_currency,
                'value_in_currency':line_id.new_value_in_currency
            })
            lines = []
            for move_line in  line_id.layer_id.account_move_id.line_ids.filtered(lambda x: x.product_id == self.product_id):
                multiplier = 1 if move_line.amount_currency >= 0 else -1
                lines.append(Command.update(move_line.id,{'amount_currency': line_id.new_value_in_currency * multiplier}))
            if lines:
                line_id.layer_id.account_move_id.line_ids = lines

        self.product_id.with_company(self.company_id.id).with_context(
            disable_auto_svl=True
            ).sudo().write({'standard_price_in_currency': self.final_amount_in_currency})
        AccountMoveLine._check_reconciliation = orig_check_reconciliation


class StockValuationLayerRecomputeLine(models.model):

    _name = 'stock.valuation.layer.recompute.line'
    _description = "lines layer recompute"



    #layer_unit_cost = fields.Monetary('Unit Value in currency', compute="_compute_other_currency_values", currency_field='valuation_currency_id', store=True)
    #layer_value = fields.Monetary('Total Value incurrency', compute="_compute_other_currency_values", currency_field='valuation_currency_id', store=True)

    layer_id = fields.Many2one('stock.valuation.layer')
    quantity = fields.Float(related="layer_id.quantity")
    quantity_at_time = fields.Float()
    layer_date = fields.Datetime(related="layer_id.create_date")
    recompute_id = fields.Many2one('stock.valuation.layer.recompute')
    currency_id = fields.Many2one('res.currency', related='recompute_id.valuation_currency_id')
    layer_unit_cost_in_currency = fields.Monetary(related="layer_id.unit_cost_in_currency")
    layer_value_in_currency = fields.Monetary(related="layer_id.value_in_currency")
    new_unit_cost_in_currency = fields.Monetary()
    new_value_in_currency = fields.Monetary()
    standard_price_in_currency = fields.Monetary()
    need_changes = fields.Boolean()
    svl_type = fields.Char()
