from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero, format_list


class StockValuationLayerRevaluation(models.TransientModel):
    _inherit = "stock.valuation.layer.revaluation"

    show_added_value_in_currency = fields.Boolean(
        compute="_compute_show_added_value_in_currency",
    )
    valuation_currency_id = fields.Many2one(
        "res.currency", string="Secondary Currency Valuation", compute="_compute_valuation_currency_id"
    )
    added_value_in_currency = fields.Monetary(
        "Added value in currency",
        compute="_compute_added_value_in_currency",
        store=True,
        readonly=False,
    )
    new_value_in_currency = fields.Monetary(
        "New value in currency",
        compute="_compute_new_value_in_currency",
    )
    new_value_in_currency_by_qty = fields.Monetary(
        "New value in currency by quantity",
        compute="_compute_new_value",
    )

    @api.depends("product_id", "company_id")
    def _compute_valuation_currency_id(self):
        for rec in self:
            product_id = rec.product_id.with_company(rec.company_id)
            rec.valuation_currency_id = product_id.categ_id.valuation_currency_id

    @api.depends("product_id", "company_id")
    def _compute_show_added_value_in_currency(self):
        for rec in self:
            product_id = rec.product_id.with_company(rec.company_id)
            rec.show_added_value_in_currency = (
                product_id.categ_id.property_cost_method in ("average", "fifo")
                and product_id.categ_id.valuation_currency_id
            )

    @api.depends("added_value", "valuation_currency_id")
    def _compute_added_value_in_currency(self):
        for rec in self:
            product_id = rec.product_id.with_company(rec.company_id)
            if (
                product_id.categ_id.property_cost_method in ("average", "fifo")
                and product_id.categ_id.valuation_currency_id
            ):
                # Update the stardard price in currency in case of AVCO
                # Para actualizar el costo en currency vuelvo a calcular el valor en moneda
                # Si bien hago dos veces el calculo (en el layer y aqui) esto es mas
                # sencillo que obtener el ultimo layer y agregar el valor.
                rec.added_value_in_currency = rec.currency_id._convert(
                    rec.added_value,
                    product_id.categ_id.valuation_currency_id,
                    rec.company_id,
                    fields.Date.today(),
                )
            else:
                rec.added_value_in_currency = 0

    @api.depends("current_quantity_svl", "added_value_in_currency", "company_id")
    def _compute_new_value_in_currency(self):
        for reval in self:
            product_id = reval.product_id.with_company(reval.company_id)
            reval.new_value_in_currency = product_id.standard_price_in_currency + reval.added_value_in_currency
            if not float_is_zero(reval.current_quantity_svl, precision_rounding=self.product_id.uom_id.rounding):
                reval.new_value_in_currency_by_qty = reval.new_value_in_currency / reval.current_quantity_svl
            else:
                reval.new_value_in_currency_by_qty = 0.0

    def action_validate_revaluation(self):
        product_id = self.product_id.with_company(self.company_id)
        if (
            product_id.categ_id.property_cost_method in ("average", "fifo")
            and product_id.categ_id.valuation_currency_id
        ):
            if self.currency_id.is_zero(self.added_value) and self.currency_id.is_zero(self.added_value_in_currency):
                raise UserError(_("The added value doesn't have any impact on the stock valuation"))

            product_id = self.product_id.with_company(self.company_id)
            lot_id = self.lot_id.with_company(self.company_id)

            remaining_domain = [
                ("product_id", "=", product_id.id),
                ("remaining_qty", ">", 0),
                ("company_id", "=", self.company_id.id),
            ]
            if lot_id:
                remaining_domain.append(("lot_id", "=", lot_id.id))
            layers_with_qty = self.env["stock.valuation.layer"].search(remaining_domain)
            adjusted_layers = self.adjusted_layer_ids or layers_with_qty

            description = _("Manual Stock Valuation: %s.", self.reason or _("No Reason Given"))
            # Update the stardard price in case of AVCO/FIFO
            cost_method = product_id.categ_id.property_cost_method
            if cost_method in ["average", "fifo"]:
                previous_cost = lot_id.standard_price if lot_id else product_id.standard_price
                total_product_qty = sum(layers_with_qty.mapped("remaining_qty"))
                if lot_id:
                    lot_id.with_context(disable_auto_svl=True).standard_price += self.added_value / total_product_qty
                product_id.with_context(disable_auto_svl=True).standard_price += (
                    self.added_value / product_id.quantity_svl
                )
                if self.lot_id:
                    description += _(
                        " lot/serial number cost updated from %(previous)s to %(new_cost)s.",
                        previous=previous_cost,
                        new_cost=lot_id.standard_price,
                    )
                else:
                    description += _(
                        " Product cost updated from %(previous)s to %(new_cost)s.",
                        previous=previous_cost,
                        new_cost=product_id.standard_price,
                    )

            revaluation_svl_vals = {
                "company_id": self.company_id.id,
                "product_id": product_id.id,
                "description": description,
                "value": self.added_value,
                "value_in_currency": self.added_value_in_currency,
                "lot_id": self.lot_id.id,
                "quantity": 0,
            }

            qty_by_lots = defaultdict(float)

            remaining_qty = sum(adjusted_layers.mapped("remaining_qty"))
            remaining_value = self.added_value
            remaining_value_unit_cost = self.currency_id.round(remaining_value / remaining_qty)

            # adjust all layers by the unit value change per unit, except the last layer which gets
            # whatever is left. This avoids rounding issues e.g. $10 on 3 products => 3.33, 3.33, 3.34
            for svl in adjusted_layers:
                if product_id.lot_valuated and not lot_id:
                    qty_by_lots[svl.lot_id.id] += svl.remaining_qty
                if float_is_zero(svl.remaining_qty - remaining_qty, precision_rounding=self.product_id.uom_id.rounding):
                    taken_remaining_value = remaining_value
                else:
                    taken_remaining_value = remaining_value_unit_cost * svl.remaining_qty
                if (
                    float_compare(
                        svl.remaining_value + taken_remaining_value,
                        0,
                        precision_rounding=self.product_id.uom_id.rounding,
                    )
                    < 0
                ):
                    raise UserError(
                        _(
                            "The value of a stock valuation layer cannot be negative. Landed cost could be use to correct a specific transfer."
                        )
                    )

                svl.remaining_value += taken_remaining_value
                remaining_value -= taken_remaining_value
                remaining_qty -= svl.remaining_qty

            previous_value_svl = self.current_value_svl

            if qty_by_lots:
                vals = revaluation_svl_vals.copy()
                total_qty = sum(adjusted_layers.mapped("remaining_qty"))
                revaluation_svl_vals = []
                for lot, qty in qty_by_lots.items():
                    value = self.added_value * qty / total_qty
                    value_in_currency = self.added_value_in_currency * qty / total_qty
                    revaluation_svl_vals.append(
                        dict(vals, value=value, lot_id=lot, value_in_currency=value_in_currency)
                    )
            revaluation_svl = self.env["stock.valuation.layer"].create(revaluation_svl_vals)

            # If the Inventory Valuation of the product category is automated, create related account move.
            if self.property_valuation != "real_time":
                return True

            accounts = product_id.product_tmpl_id.get_product_accounts()

            if self.added_value < 0 or self.added_value_in_currency < 0:
                debit_account_id = self.account_id.id
                credit_account_id = accounts.get("stock_valuation") and accounts["stock_valuation"].id
            else:
                debit_account_id = accounts.get("stock_valuation") and accounts["stock_valuation"].id
                credit_account_id = self.account_id.id

            move_description = _(
                "%(user)s changed stock valuation from  %(previous)s to %(new_value)s - %(product)s\n%(reason)s",
                user=self.env.user.name,
                previous=previous_value_svl,
                new_value=previous_value_svl + self.added_value,
                product=product_id.display_name,
                reason=description,
            )

            if self.adjusted_layer_ids:
                adjusted_layer_descriptions = [
                    f"{layer.reference} (id: {layer.id})" for layer in self.adjusted_layer_ids
                ]
                move_description += _(
                    "\nAffected valuation layers: %s", format_list(self.env, adjusted_layer_descriptions)
                )

            move_vals = [
                {
                    "journal_id": self.account_journal_id.id or accounts["stock_journal"].id,
                    "company_id": self.company_id.id,
                    "ref": _("Revaluation of %s", product_id.display_name),
                    "stock_valuation_layer_ids": [(6, None, [svl.id])],
                    "date": self.date or fields.Date.today(),
                    "move_type": "entry",
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "name": move_description,
                                "account_id": debit_account_id,
                                "debit": abs(svl.value),
                                "credit": 0,
                                "amount_currency": abs(svl.value_in_currency),
                                "product_id": svl.product_id.id,
                                "currency_id": product_id.categ_id.valuation_currency_id.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "name": move_description,
                                "account_id": credit_account_id,
                                "debit": 0,
                                "amount_currency": abs(svl.value_in_currency) * -1,
                                "credit": abs(svl.value),
                                "product_id": svl.product_id.id,
                                "currency_id": product_id.categ_id.valuation_currency_id.id,
                            },
                        ),
                    ],
                }
                for svl in revaluation_svl
            ]
            account_move = self.env["account.move"].create(move_vals)
            account_move._post()

            return True
        return super().action_validate_revaluation()
