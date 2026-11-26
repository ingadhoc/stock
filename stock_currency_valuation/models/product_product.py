from collections import defaultdict
from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.fields import Domain


class productProduct(models.Model):
    _inherit = "product.product"

    valuation_currency_id = fields.Many2one(
        related="categ_id.valuation_currency_id",
    )
    standard_price_in_currency = fields.Float(
        "Cost in currency",
        company_dependent=True,
        groups="base.group_user",
        help="Cost of the product expressed in the secondary currency defined on the product category. Used for inventory valuation and cost calculations in that currency.",
    )
    avg_cost_in_currency = fields.Monetary(
        string="Average Cost (Currency)",
        compute="_compute_value_in_currency",
        compute_sudo=True,
        currency_field="valuation_currency_id",
    )
    total_value_in_currency = fields.Monetary(
        string="Total Value (Currency)",
        compute="_compute_value_in_currency",
        compute_sudo=True,
        currency_field="valuation_currency_id",
    )

    def write(self, vals):
        old_price_in_currency = False
        if "standard_price_in_currency" in vals and not self.env.context.get("disable_auto_revaluation"):
            old_price_in_currency = {product: product.standard_price_in_currency for product in self}
        res = super(productProduct, self.with_context(old_price_in_currency=old_price_in_currency)).write(vals)
        # With standard_price in vals, the core write already called _change_standard_price.
        if old_price_in_currency and "standard_price" not in vals:
            self.with_context(old_price_in_currency=old_price_in_currency)._change_standard_price(
                {product: product.standard_price for product in self}
            )
        return res

    @api.depends_context("to_date", "company", "warehouse_id")
    @api.depends("cost_method", "stock_move_ids.value_in_currency", "standard_price_in_currency")
    def _compute_value_in_currency(self):
        # Only meaningful for products that have a secondary valuation currency.
        # Products without one get zeroed out and we skip heavy computation for them.
        for product in self.filtered(lambda p: not p.valuation_currency_id):
            product.avg_cost_in_currency = 0
            product.total_value_in_currency = 0

        products = self.filtered(lambda p: p.valuation_currency_id)
        if not products:
            return

        products = products._with_valuation_context()

        at_date = self.env.company._to_datetime_upper_bound(self.env.context.get("to_date"))
        if at_date:
            products = products.with_context(at_date=at_date)

        avg_cost_in_currency_by_product_id = {}
        total_value_in_currency_by_product_id = {}
        ratio_by_product_id = {}

        product_ids_grouped_by_cost_method = defaultdict(set)
        for product in products:
            if product.lot_valuated:
                # lot-valuated: not handled here, zero out
                avg_cost_in_currency_by_product_id[product.id] = 0
                total_value_in_currency_by_product_id[product.id] = 0
                continue
            product_whole_company_context = product.with_context(warehouse_id=False)
            if product.uom_id.is_zero(product.qty_available):
                total_value_in_currency_by_product_id[product.id] = 0
                avg_cost_in_currency_by_product_id[product.id] = product.standard_price_in_currency
                continue
            if product.uom_id.is_zero(product_whole_company_context.qty_available):
                total_value_in_currency_by_product_id[product.id] = (
                    product.standard_price_in_currency * product.qty_available
                )
                avg_cost_in_currency_by_product_id[product.id] = product.standard_price_in_currency
                continue
            if product.uom_id.compare(product.qty_available, product_whole_company_context.qty_available) != 0:
                ratio_by_product_id[product.id] = product.qty_available / product_whole_company_context.qty_available
            product_ids_grouped_by_cost_method[product.cost_method].add(product.id)

        for cost_method, product_ids in product_ids_grouped_by_cost_method.items():
            batch = self.env["product.product"].browse(product_ids).with_context(warehouse_id=False)
            if cost_method == "standard":
                avg_costs, total_values = batch._run_standard_in_currency(at_date=at_date)
            elif cost_method == "average":
                avg_costs, total_values = batch._run_avco_in_currency(at_date=at_date, force_recompute=True)
            else:
                avg_costs, total_values = batch._run_fifo_in_currency(at_date=at_date)
            avg_cost_in_currency_by_product_id.update(avg_costs)
            total_value_in_currency_by_product_id.update(total_values)

        for product in self.filtered(lambda p: p.valuation_currency_id):
            product.avg_cost_in_currency = avg_cost_in_currency_by_product_id.get(
                product.id, product.standard_price_in_currency
            )
            product.total_value_in_currency = total_value_in_currency_by_product_id.get(
                product.id, 0
            ) * ratio_by_product_id.get(product.id, 1)

    # -------------------------------------------------------------------------
    # Private
    # -------------------------------------------------------------------------

    def _change_standard_price(self, old_price, valuation_date=None):
        super()._change_standard_price(old_price, valuation_date=valuation_date)
        # The core skips a product whose cost in company currency did not change.
        old_price_in_currency = self.env.context.get("old_price_in_currency") or {}
        date = valuation_date or fields.Datetime.now()
        product_values = []
        for product in self.filtered("valuation_currency_id"):
            old_in_currency = old_price_in_currency.get(product)
            if (
                product not in old_price_in_currency
                or not product.is_storable
                or product.cost_method == "fifo"
                or product.standard_price != old_price.get(product)
                or product.standard_price_in_currency == old_in_currency
            ):
                continue
            quantity = product.with_context(to_date=date).sudo().qty_available
            value = product.standard_price
            product_values.append(
                {
                    "product_id": product.id,
                    "quantity": quantity,
                    "old_cost": value,
                    "new_cost": value,
                    "old_value": value * quantity,
                    "new_value": value * quantity,
                    "value": value,
                    "value_in_currency": product.standard_price_in_currency,
                    "previous_value_in_currency": old_in_currency,
                    "company_id": product.company_id.id or self.env.company.id,
                    "date": date,
                    "description": self.env._(
                        "Cost in currency update from %(old_value)s to %(new_value)s for %(quantity)s by %(user)s",
                        old_value=old_in_currency,
                        new_value=product.standard_price_in_currency,
                        quantity=quantity,
                        user=self.env.user.name,
                    ),
                }
            )
        self.env["product.value"].sudo().create(product_values)

    def _correct_inventory_valuation(self, from_date):
        """Follow the core replay in the secondary currency.

        FIFO keeps the 19 criterion (no layers in currency), so a corrected outgoing move
        moves its amount in currency in the same proportion as its company value.
        """
        products = self.filtered(lambda p: p.valuation_currency_id and not p.lot_valuated)
        boundary = from_date - timedelta(seconds=1) if from_date != datetime.min else from_date
        moves_by_product = products.filtered(
            lambda p: p.cost_method == "fifo"
        )._get_stock_moves_with_valuation_by_product(boundary)
        old_fifo_values = {
            move.id: move.value for moves in moves_by_product.values() for move in moves.filtered("is_out")
        }
        changed_moves = super()._correct_inventory_valuation(from_date)
        for cost_method, method_products in products.grouped("cost_method").items():
            if cost_method == "standard":
                method_products._run_standard_in_currency(at_date=from_date, correction=True)
            elif cost_method == "average":
                method_products._run_avco_in_currency(at_date=from_date, correction=True)
        for move in changed_moves.filtered(lambda m: m.id in old_fifo_values):
            old_value = old_fifo_values[move.id]
            if old_value:
                move.value_in_currency = move.value_in_currency * move.value / old_value
            else:
                product = move.product_id.with_company(move.company_id)
                move.value_in_currency = move._get_valued_qty(signed=True) * product.standard_price_in_currency
        return changed_moves

    def _run_standard_in_currency(self, at_date=None, lot=None, correction=False):
        """Twin of _run_standard, reading the cost in the secondary currency."""
        if at_date and correction and at_date != datetime.min:
            at_date = at_date - timedelta(seconds=1)
        std_price_by_product_id = {p.id: p.standard_price_in_currency for p in self}
        if at_date:
            last_value_by_product = self.with_context(
                exclude_min_valuation_date=not correction
            )._get_last_product_value(at_date, lot=lot)
            std_price_by_product_id = {
                p.id: (
                    last_value_by_product[p].value_in_currency
                    if p in last_value_by_product
                    else p.standard_price_in_currency
                )
                for p in self
            }
        value_by_product_id = {p.id: p.qty_available * std_price_by_product_id.get(p.id, 0) for p in self}
        if not correction:
            return std_price_by_product_id, value_by_product_id

        moves_by_product = self._get_stock_moves_with_valuation_by_product(at_date)
        price_history_by_product = self._get_std_price_history_by_product(at_date)
        for product in self:
            std_price = std_price_by_product_id.get(product.id, product.standard_price_in_currency)
            price_changes = iter(price_history_by_product.get(product, self.env["product.value"]))
            next_change = next(price_changes, None)
            for move in moves_by_product.get(product, self.env["stock.move"]):
                while next_change and next_change.date <= move.date:
                    std_price = next_change.value_in_currency
                    next_change = next(price_changes, None)
                if move.is_out:
                    move.value_in_currency = move._get_valued_qty(signed=True) * std_price
        return std_price_by_product_id, value_by_product_id

    def _run_fifo_in_currency(self, at_date=None, lot=None):
        """Twin of _run_fifo: translates the FIFO stack value (company currency) to the
        valuation currency using today's exchange rate."""
        std_price_in_currency_by_product_id = {}
        value_in_currency_by_product_id = {}
        for product in self:
            quantity = product.qty_available
            value = product._run_fifo(at_date=at_date, lot=lot)[1].get(product.id, 0)
            if value and product.valuation_currency_id:
                # product.company_id is empty on shared products and _convert would then apply rate 1
                company = product.company_id or self.env.company
                value_in_currency = company.currency_id._convert(
                    from_amount=value,
                    to_currency=product.valuation_currency_id,
                    company=company,
                    date=fields.Date.today(),
                )
            else:
                value_in_currency = 0
            std_price = value_in_currency / quantity if quantity else 0
            std_price_in_currency_by_product_id[product.id] = std_price
            value_in_currency_by_product_id[product.id] = value_in_currency
        return std_price_in_currency_by_product_id, value_in_currency_by_product_id

    def _run_avco_in_currency(self, at_date=None, lot=None, force_recompute=False, correction=False):
        """Twin of _run_avco, replaying value_in_currency. With ``correction`` it rewrites
        the amount in currency of the outgoing moves after ``at_date``."""
        if at_date and correction and at_date != datetime.min:
            at_date = at_date - timedelta(seconds=1)
        std_price_by_product_id = {}
        value_by_product_id = {}
        quantity_by_product_id = {}

        products = self.filtered(lambda p: p.valuation_currency_id)
        if not products:
            return std_price_by_product_id, value_by_product_id

        if not at_date and not force_recompute:
            std_price_by_product_id = {p.id: p.standard_price_in_currency for p in products}
            value_by_product_id = {p.id: p.qty_available * std_price_by_product_id[p.id] for p in products}
            return std_price_by_product_id, value_by_product_id

        moves_domain = Domain(
            [
                ("product_id", "in", products._as_query()),
                ("company_id", "=", self.env.company.id),
                "|",
                ("is_in", "=", True),
                ("is_out", "=", True),
            ]
        )
        if lot:
            moves_domain &= Domain([("move_line_ids.lot_id", "in", lot.id)])
        if at_date and not correction:
            moves_domain &= Domain([("date", "<=", at_date)])

        from_date_by_product_id = {}
        for manual_value in products._get_last_product_value(at_date, lot=lot).values():
            product = manual_value.product_id
            if lot:
                quantity = lot.with_context(
                    to_date=manual_value.date, allowed_company_ids=self.env.company.ids
                ).product_qty
            else:
                quantity = product.with_context(
                    to_date=manual_value.date, allowed_company_ids=self.env.company.ids
                ).qty_available
            std_price_by_product_id[product.id] = manual_value.value_in_currency
            quantity_by_product_id[product.id] = quantity
            value_by_product_id[product.id] = manual_value.value_in_currency * quantity
            from_date_by_product_id[product.id] = manual_value.date

        price_history_by_product = products._get_std_price_history_by_product(at_date) if correction else {}
        moves = self.env["stock.move"].search(moves_domain, order="product_id, date, id")
        for product, product_moves in moves.grouped("product_id").items():
            quantity = quantity_by_product_id.get(product.id, 0)
            average_cost = std_price_by_product_id.get(product.id)
            value = value_by_product_id.get(product.id, 0)
            valuation_from_date = from_date_by_product_id.get(product.id)
            price_changes = iter(price_history_by_product.get(product, self.env["product.value"]))
            next_change = next(price_changes, None)
            for move in product_moves:
                if valuation_from_date and move.date <= valuation_from_date:
                    continue
                if average_cost is None:
                    valued_qty = move._get_valued_qty()
                    average_cost = abs(move.value_in_currency) / valued_qty if valued_qty else 0
                while next_change and next_change.date <= move.date:
                    average_cost = next_change.value_in_currency
                    value = average_cost * quantity
                    next_change = next(price_changes, None)
                if move.is_in:
                    in_qty = move._get_valued_qty()
                    in_value = move.value_in_currency
                    if lot:
                        lot_qty = move._get_valued_qty(lot)
                        in_value = (in_value * lot_qty / in_qty) if in_qty else 0
                        in_qty = lot_qty
                    previous_qty = quantity
                    quantity += in_qty
                    if previous_qty > 0:
                        value += in_value
                        average_cost = value / quantity
                    else:
                        average_cost = in_value / in_qty if in_qty else average_cost
                        value = average_cost * quantity
                if move.is_out:
                    out_qty = move._get_valued_qty()
                    out_value = out_qty * average_cost
                    if lot:
                        lot_qty = move._get_valued_qty(lot)
                        out_value = (out_value * lot_qty / out_qty) if out_qty else 0
                        out_qty = lot_qty
                    if correction and move.date > at_date:
                        move.value_in_currency = -out_value
                    value -= out_value
                    quantity -= out_qty
            std_price_by_product_id[product.id] = average_cost or 0
            value_by_product_id[product.id] = value
            quantity_by_product_id[product.id] = quantity
        return std_price_by_product_id, value_by_product_id

    def _update_standard_price(self, extra_value=None, extra_quantity=None):
        """Extiende _update_standard_price para también actualizar standard_price_in_currency
        en productos que tienen valuation_currency_id definido."""
        super()._update_standard_price(extra_value=extra_value, extra_quantity=extra_quantity)

        products_with_currency = self.filtered(lambda p: p.valuation_currency_id and not p.lot_valuated)
        if not products_with_currency or self.env.context.get("skip_standard_price_in_currency"):
            return

        # Agrupar por cost_method para actualizar standard_price_in_currency
        products_by_cost_method = defaultdict(lambda: self.env["product.product"])
        for product in products_with_currency:
            products_by_cost_method[product.cost_method] |= product

        for cost_method, products in products_by_cost_method.items():
            if cost_method == "standard":
                # Para precio estándar no hay recálculo automático de AVCO;
                # el usuario debe actualizar standard_price_in_currency manualmente.
                continue

            if cost_method == "average":
                new_prices_in_currency = products._run_avco_in_currency(force_recompute=True)[0]
                for product in products:
                    if product.id in new_prices_in_currency:
                        product.with_context(
                            disable_auto_revaluation=True
                        ).sudo().standard_price_in_currency = new_prices_in_currency[product.id]
                continue

            if cost_method == "fifo":
                # Para FIFO: ratio entre standard_price_in_currency y standard_price
                # proporcional al último precio de entrada, usando la tasa de la moneda actual.
                for product in products:
                    qty_available = product._with_valuation_context().qty_available
                    if product.uom_id.compare(qty_available, 0) > 0 and product.standard_price:
                        # Calcular usando la tasa de cambio actual entre company_currency y valuation_currency
                        company = product.company_id or self.env.company
                        new_price_in_currency = company.currency_id._convert(
                            from_amount=product.standard_price,
                            to_currency=product.valuation_currency_id,
                            company=company,
                            date=fields.Date.today(),
                        )
                        product.with_context(
                            disable_auto_revaluation=True
                        ).sudo().standard_price_in_currency = new_price_in_currency
