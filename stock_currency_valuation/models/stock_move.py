from collections import defaultdict

from odoo import fields, models
from odoo.tools.float_utils import float_compare, float_is_zero


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_price_unit(self):
        # Esto modifica el precio moneda de la compañia basandose en el valor la cotizacoin
        # del dolar agregado en el picking.
        # TODO: pude fallar si los lotes de un mismo producto tiene diferentes costos
        self.ensure_one()
        price_units = super()._get_price_unit()
        for index in price_units.items():
            if (
                self.picking_id.currency_rate
                and self.purchase_line_id.order_id.currency_id == self.picking_id.valuation_currency_id
            ):
                price_units[index[0]] = self.purchase_line_id.price_unit / self.picking_id.currency_rate
        return price_units

    def _account_entry_move(self, qty, description, svl_id, cost):
        am_vals_list = super()._account_entry_move(qty, description, svl_id, cost)
        layer = self.env["stock.valuation.layer"].browse(svl_id)
        if layer.valuation_currency_id:
            for am_vals in am_vals_list:
                for line_id in am_vals["line_ids"]:
                    sign = -1 if line_id[2]["balance"] < 0 else 1
                    line_id[2].update(
                        {
                            "currency_id": layer.valuation_currency_id.id,
                            "amount_currency": abs(layer.value_in_currency) * sign,
                        }
                    )
        return am_vals_list

    def product_price_update_before_done(self, forced_qty=None):
        super().product_price_update_before_done(forced_qty=forced_qty)
        # Actualizo tambien el costo en moneda
        tmpl_dict = defaultdict(lambda: 0.0)
        # adapt standard price on incomming moves if the product cost_method is 'average'
        std_price_update = {}
        for move in self.filtered(
            lambda move: move._is_in()
            and move.with_company(move.company_id).product_id.categ_id.valuation_currency_id
            and move.with_company(move.company_id).product_id.cost_method == "average"
        ):
            product_tot_qty_available = (
                move.product_id.sudo().with_company(move.company_id).quantity_svl + tmpl_dict[move.product_id.id]
            )
            rounding = move.product_id.uom_id.rounding

            valued_move_lines = move._get_in_move_lines()
            qty_done = 0
            for valued_move_line in valued_move_lines:
                qty_done += valued_move_line.product_uom_id._compute_quantity(
                    valued_move_line.qty_done, move.product_id.uom_id
                )

            qty = forced_qty or qty_done
            if float_is_zero(product_tot_qty_available, precision_rounding=rounding):
                new_std_price_in_currency = move._get_currency_price_unit(
                    default=move.product_id.standard_price_in_currency
                )
            elif float_is_zero(
                product_tot_qty_available + move.product_qty, precision_rounding=rounding
            ) or float_is_zero(product_tot_qty_available + qty, precision_rounding=rounding):
                new_std_price_in_currency = move._get_currency_price_unit(
                    default=move.product_id.standard_price_in_currency
                )
            else:
                # Get the standard price
                amount_unit = (
                    std_price_update.get((move.company_id.id, move.product_id.id))
                    or move.product_id.with_company(move.company_id).standard_price_in_currency
                )
                new_std_price_in_currency = (
                    (amount_unit * product_tot_qty_available) + (move._get_currency_price_unit() * qty)
                ) / (product_tot_qty_available + qty)

            tmpl_dict[move.product_id.id] += qty_done
            # Write the standard price, as SUPERUSER_ID because a warehouse manager may not have the right to write on products
            move.product_id.with_company(move.company_id.id).with_context(disable_auto_svl=True).sudo().write(
                {"standard_price_in_currency": new_std_price_in_currency}
            )

            std_price_update[move.company_id.id, move.product_id.id] = new_std_price_in_currency
        # adapt standard price on incomming moves if the product cost_method is 'fifo'
        for move in self.filtered(
            lambda move: move.with_company(move.company_id).product_id.cost_method == "fifo"
            and float_is_zero(move.product_id.sudo().quantity_svl, precision_rounding=move.product_id.uom_id.rounding)
        ):
            move.product_id.with_company(move.company_id.id).sudo().write(
                {"standard_price_in_currency": move._get_currency_price_unit()}
            )

    def _get_currency_price_unit(self, default=0.0):
        """Returns the unit price from this stock move"""
        self.ensure_one()
        currency_id = self.company_id.currency_id
        if hasattr(self, "purchase_order_Line") and self.purchase_order_Line:
            currency_id = self.purchase_order_Line.currency_id
        if hasattr(self, "sale_line_id") and self.sale_line_id:
            currency_id = self.sale_line_id.currency_id

        price_unit = currency_id._convert(
            from_amount=self.price_unit,
            to_currency=self.product_id.categ_id.valuation_currency_id,
            company=self.company_id,
            date=fields.date.today(),
        )
        precision = self.env["decimal.precision"].precision_get("Product Price")
        # If the move is a return, use the original move's price unit.
        if self.origin_returned_move_id and self.origin_returned_move_id.sudo().stock_valuation_layer_ids:
            layers = self.origin_returned_move_id.sudo().stock_valuation_layer_ids
            # dropshipping create additional positive svl to make sure there is no impact on the stock valuation
            # We need to remove them from the computation of the price unit.
            if (
                self.origin_returned_move_id._is_dropshipped()
                or self.origin_returned_move_id._is_dropshipped_returned()
            ):
                layers = layers.filtered(
                    lambda l: float_compare(l.value, 0, precision_rounding=l.product_id.uom_id.rounding) <= 0
                )
            layers |= layers.stock_valuation_layer_ids
            quantity = sum(layers.mapped("quantity"))
            return (
                sum(layers.mapped("value_in_currency")) / quantity
                if not float_is_zero(quantity, precision_rounding=layers.uom_id.rounding)
                else 0
            )
        return price_unit if not float_is_zero(price_unit, precision) or self._should_force_price_unit() else default
