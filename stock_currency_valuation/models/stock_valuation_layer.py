from odoo import api, fields, models
from odoo.tools.float_utils import float_is_zero


class StockValuationLayer(models.Model):
    _inherit = "stock.valuation.layer"

    valuation_currency_id = fields.Many2one(related="categ_id.valuation_currency_id")
    unit_cost_in_currency = fields.Monetary(
        "Unit Value in currency",
        compute="_compute_other_currency_values",
        currency_field="valuation_currency_id",
        store=True,
    )
    value_in_currency = fields.Monetary(
        "Total Value incurrency",
        compute="_compute_other_currency_values",
        currency_field="valuation_currency_id",
        store=True,
    )
    product_tmpl_id = fields.Many2one(store=True)
    bypass_currency_valuation = fields.Boolean()
    manual_currency_rate = fields.Float(store=True, digits=0, compute="_compute_manual_currency_rate")

    def move_is_return(self):
        return bool(
            self.stock_move_id.origin_returned_move_id
            and self.stock_move_id.origin_returned_move_id.sudo().stock_valuation_layer_ids
        )

    @api.depends("stock_landed_cost_id", "stock_move_id")
    def _compute_manual_currency_rate(self):
        for rec in self:
            if rec.stock_landed_cost_id:
                rec.manual_currency_rate = rec.stock_landed_cost_id.currency_rate
            elif rec.stock_move_id:
                rec.manual_currency_rate = rec.stock_move_id.picking_id.currency_rate
            else:
                rec.manual_currency_rate = False

    @api.depends("categ_id", "value", "bypass_currency_valuation", "stock_valuation_layer_id", "manual_currency_rate")
    def _compute_other_currency_values(self):
        for rec in self:
            # Agrego este hack para evitar recomputar este campo luego de la
            # creacion del registro cuando lo llamo desde action_validate_revaluation (╥﹏╥)
            # Otra posibilidad es remplazar el metodo del wizard cuando el producto tiene moneda secundaria.
            rec = rec.with_company(rec.company_id.id)
            if rec.value_in_currency:
                continue
            # rec.stock_valuation_layer_id
            if not rec.bypass_currency_valuation and rec.valuation_currency_id:
                if rec.stock_move_id and (rec.stock_move_id._is_out() or rec.stock_move_id.is_inventory):
                    # Si el movimento es de salida o de inventario, valor es el registrado en el producto
                    rec.value_in_currency = (
                        rec.product_id.with_company(rec.company_id.id).standard_price_in_currency * rec.quantity
                    )
                elif rec.stock_move_id and rec.stock_move_id._is_returned(valued_type="in"):
                    # Si es una devolucion y existe el movimiento de origen
                    # el valor de avco sale del mov de origen sino sale de producto
                    if rec.stock_move_id.origin_returned_move_id:
                        unit_cost_in_currency = (
                            rec.stock_move_id.origin_returned_move_id.stock_valuation_layer_ids.unit_cost_in_currency
                        )
                        rec.value_in_currency = unit_cost_in_currency * rec.quantity
                    else:
                        rec.value_in_currency = (
                            rec.product_id.with_company(rec.company_id.id).standard_price_in_currency * rec.quantity
                        )
                elif rec.manual_currency_rate:
                    rec.value_in_currency = rec.value * rec.manual_currency_rate
                else:
                    rec.value_in_currency = rec.currency_id._convert(
                        from_amount=rec.value,
                        to_currency=rec.valuation_currency_id,
                        company=rec.company_id,
                        date=rec.create_date,
                    )
                if rec.quantity:
                    rec.unit_cost_in_currency = abs(rec.value_in_currency / rec.quantity)
                else:
                    rec.unit_cost_in_currency = False
            else:
                rec.value_in_currency = False
                rec.unit_cost_in_currency = False

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res._update_currency_standard_price()
        return res

    def _update_currency_standard_price(self):
        for layer_id in self.filtered(
            lambda x: x.stock_landed_cost_id and x.product_id.cost_method == "average" and x.value_in_currency
        ):
            # batch standard price computation avoid recompute quantity_svl at each iteration
            product = layer_id.product_id.with_company(layer_id.company_id)
            if not float_is_zero(product.quantity_svl, precision_rounding=product.uom_id.rounding):
                product.sudo().with_context(disable_auto_svl=True).standard_price_in_currency += (
                    layer_id.value_in_currency / product.quantity_svl
                )
