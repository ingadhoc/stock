from bisect import bisect
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.fields import Domain
from odoo.tools import SQL


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
        old_price = False
        old_price_in_currency = False
        require_standard_price_compute = "standard_price_in_currency" in vals and not self.env.context.get(
            "disable_auto_revaluation"
        )
        if require_standard_price_compute:
            # old_price se captura igual que old_price_in_currency (antes de escribir):
            # _change_standard_price compara ambos para decidir si el precio realmente
            # cambió. Pasarle {} en vez de esto comparaba siempre contra None, así que la
            # guarda de "no cambió" nunca se cumplía y cada write creaba un product.value
            # espurio (ver TESTING.md, caso 2.5).
            old_price = {product: product.standard_price for product in self}
            old_price_in_currency = {product: product.standard_price_in_currency for product in self}
        res = super(productProduct, self.with_context(old_price_in_currency=old_price_in_currency)).write(vals)
        if old_price_in_currency:
            self.with_context(old_price_in_currency=old_price_in_currency)._change_standard_price(old_price)
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

        at_date = fields.Datetime.to_datetime(self.env.context.get("to_date"))
        if at_date:
            at_date = at_date.replace(hour=23, minute=59, second=59)
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
                avg_costs, total_values = batch._run_standard_batch_in_currency(at_date=at_date)
            elif cost_method == "average":
                avg_costs, total_values = batch._run_average_batch_in_currency(at_date=at_date, force_recompute=True)
            else:
                avg_costs, total_values = batch._run_fifo_batch_in_currency(at_date=at_date)
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

    def _change_standard_price(self, old_price):
        with_valuation_currency = self.filtered(lambda x: x.valuation_currency_id)
        super(productProduct, self - with_valuation_currency)._change_standard_price(old_price)
        old_price_in_currency = self.env.context.get("old_price_in_currency") or {}
        # Mismo criterio que el core: respetar valuation_date (p.ej. datetime.min al crear
        # el producto). Hardcodear now() fechaba el product.value inicial en la fecha real,
        # y _run_average_batch_in_currency lo tomaba como "último valor manual", filtrando
        # con date >= esa fecha todos los movimientos históricos reales (valor en moneda = 0).
        date = self.env.context.get("valuation_date") or fields.Datetime.now()
        for product in with_valuation_currency:
            if product.cost_method == "fifo" or (
                product.standard_price == old_price.get(product)
                and product.standard_price_in_currency == old_price_in_currency.get(product)
            ):
                continue
            self.env["product.value"].sudo().create(
                {
                    "product_id": product.id,
                    "value": product.standard_price,
                    "value_in_currency": product.standard_price_in_currency,
                    "valuation_currency_id": product.valuation_currency_id.id,
                    "company_id": product.company_id.id or self.env.company.id,
                    "date": date,
                    "description": _(
                        "Price update from %(old_price)s to %(new_price)s by %(user)s",
                        old_price=old_price.get(product) or old_price_in_currency.get(product),
                        new_price=product.standard_price,
                        user=self.env.user.name,
                    ),
                }
            )
        return

    def _get_last_product_value(self, date=None, lot=False):
        # estoy reemplazando el metodo para agregar value_in_currency.
        # es mejor ir por un monkey patch?
        domain = Domain(
            [
                ("product_id", "in", self.ids),
                ("move_id", "=", False),
                ("company_id", "=", self.env.company.id),
            ]
        )
        if lot:
            domain &= Domain(["|", ("lot_id", "=", lot.id), ("lot_id", "=", False)])
        else:
            domain &= Domain([("lot_id", "=", False)])
        if date:
            domain &= Domain([("date", "<=", date)])

        query = self.env["product.value"].sudo()._search(domain)
        query_select = SQL("distinct ON (product_value.product_id) product_value.id")
        query.order = SQL("product_value.product_id, product_value.date DESC, product_value.id DESC")
        query._ids = tuple(id_ for (id_,) in self.env.execute_query(query.select(query_select)))
        product_values = self.env["product.value"].browse(query._ids)
        product_values.sudo().fetch(["product_id", "value", "value_in_currency", "date"])
        return {pv.product_id: pv for pv in product_values}

    def _run_standard_batch_in_currency(self, at_date=None, lot=None):
        """Equivalent of _run_standard_batch but using standard_price_in_currency.
        At a given date reads the last recorded product.value.value_in_currency."""
        std_price_in_currency_by_product_id = {p.id: p.standard_price_in_currency for p in self}
        if at_date:
            product_value_by_product = self._get_last_product_value(at_date, lot=lot)
            std_price_in_currency_by_product_id = {
                p.id: (
                    product_value_by_product[p].value_in_currency
                    if p in product_value_by_product
                    else p.standard_price_in_currency
                )
                for p in self
            }
        value_by_product_id = {p.id: p.qty_available * std_price_in_currency_by_product_id.get(p.id, 0) for p in self}
        return std_price_in_currency_by_product_id, value_by_product_id

    def _run_fifo_batch_in_currency(self, at_date=None, lot=None):
        """Equivalent of _run_fifo_batch but for the secondary valuation currency.
        Translates the FIFO stack value (company currency) to valuation_currency
        using today's exchange rate."""
        std_price_in_currency_by_product_id = {}
        value_in_currency_by_product_id = {}
        for product in self:
            quantity = product.qty_available
            value = product._run_fifo(quantity, lot, at_date)
            if value and product.valuation_currency_id:
                value_in_currency = product.company_id.currency_id._convert(
                    from_amount=value,
                    to_currency=product.valuation_currency_id,
                    company=product.company_id,
                    date=fields.Date.today(),
                )
            else:
                value_in_currency = 0
            std_price = value_in_currency / quantity if quantity else 0
            std_price_in_currency_by_product_id[product.id] = std_price
            value_in_currency_by_product_id[product.id] = value_in_currency
        return std_price_in_currency_by_product_id, value_in_currency_by_product_id

    def _run_average_batch_in_currency(self, at_date=None, lot=None, force_recompute=False):
        """Replica de _run_average_batch pero calculando el costo promedio en la moneda
        secundaria (valuation_currency_id) usando value_in_currency de los moves.

        Retorna (std_price_in_currency_by_product_id, value_in_currency_by_product_id).
        Solo procesa productos que tienen valuation_currency_id definido.
        """
        std_price_in_currency_by_product_id = {}
        value_in_currency_by_product_id = {}
        quantity_by_product_id = {}

        # Solo tiene sentido para productos con moneda de valuación
        products = self.filtered(lambda p: p.valuation_currency_id)
        if not products:
            return std_price_in_currency_by_product_id, value_in_currency_by_product_id

        if not at_date and not force_recompute:
            std_price_in_currency_by_product_id = {p.id: p.standard_price_in_currency for p in products}
            value_in_currency_by_product_id = {
                p.id: p.qty_available * std_price_in_currency_by_product_id.get(p.id, 0) for p in products
            }
            return std_price_in_currency_by_product_id, value_in_currency_by_product_id

        moves_domain = Domain(
            [
                ("product_id", "in", products._as_query()),
                ("company_id", "=", self.env.company.id),
                "|",
                "|",
                ("is_in", "=", True),
                ("is_dropship", "=", True),
                ("is_out", "=", True),
            ]
        )
        if lot:
            moves_domain &= Domain([("move_line_ids.lot_id", "in", lot.id)])
        if at_date:
            moves_domain &= Domain([("date", "<=", at_date)])

        move_fields = [
            "date",
            "is_dropship",
            "is_in",
            "is_out",
            "location_dest_id",
            "location_id",
            "move_line_ids",
            "picked",
            "value",
            "value_in_currency",
            "product_id",
        ]
        last_manual_value_by_product = products._get_last_product_value(at_date, lot=lot)
        oldest_manual_value = (
            min(pv.date for pv in last_manual_value_by_product.values()) if last_manual_value_by_product else False
        )
        if oldest_manual_value:
            moves_domain &= Domain([("date", ">=", oldest_manual_value)])

        moves = self.env["stock.move"].search_fetch(
            moves_domain,
            field_names=move_fields,
            order="date, id",
        )
        moves.move_line_ids.fetch(
            [
                "company_id",
                "location_id",
                "location_dest_id",
                "lot_id",
                "owner_id",
                "picked",
                "quantity_product_uom",
            ]
        )

        moves_by_product = moves.grouped(key=lambda m: m.product_id)

        # Punto de partida: último valor manual registrado en product.value
        for manual_value in last_manual_value_by_product.values():
            product = manual_value.product_id
            quantity = product.with_context(to_date=manual_value.date).qty_available

            std_price_in_currency_by_product_id[product.id] = manual_value.value_in_currency
            quantity_by_product_id[product.id] = quantity
            value_in_currency_by_product_id[product.id] = manual_value.value_in_currency * quantity

            product_moves = moves_by_product.get(product, self.env["stock.move"])
            index = bisect(product_moves, manual_value.date, key=lambda m: m.date)
            moves_by_product[product] = product_moves[index:]

        # Reproducir el historial de valuación en moneda secundaria
        for product, product_moves in moves_by_product.items():
            quantity = quantity_by_product_id.get(product.id, 0)
            average_cost = std_price_in_currency_by_product_id.get(product.id, 0)
            value = value_in_currency_by_product_id.get(product.id, 0)

            for move in product_moves:
                if move.is_in or move.is_dropship:
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
                        average_cost = value / quantity if quantity else average_cost
                    elif previous_qty <= 0:
                        average_cost = in_value / in_qty if in_qty else average_cost
                        value = average_cost * quantity
                if move.is_out or move.is_dropship:
                    out_qty = move._get_valued_qty()
                    out_value = out_qty * average_cost
                    if lot:
                        lot_qty = move._get_valued_qty(lot)
                        out_value = (out_value * lot_qty / out_qty) if out_qty else 0
                        out_qty = lot_qty
                    value -= out_value
                    quantity -= out_qty

            std_price_in_currency_by_product_id[product.id] = average_cost
            value_in_currency_by_product_id[product.id] = value

        return std_price_in_currency_by_product_id, value_in_currency_by_product_id

    def _update_standard_price(self, extra_value=None, extra_quantity=None):
        """Extiende _update_standard_price para también actualizar standard_price_in_currency
        en productos que tienen valuation_currency_id definido."""
        super()._update_standard_price(extra_value=extra_value, extra_quantity=extra_quantity)

        products_with_currency = self.filtered(lambda p: p.valuation_currency_id and not p.lot_valuated)
        if not products_with_currency:
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
                new_prices_in_currency = products._run_average_batch_in_currency(force_recompute=True)[0]
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
                        new_price_in_currency = product.company_id.currency_id._convert(
                            from_amount=product.standard_price,
                            to_currency=product.valuation_currency_id,
                            company=product.company_id,
                            date=fields.Date.today(),
                        )
                        product.with_context(
                            disable_auto_revaluation=True
                        ).sudo().standard_price_in_currency = new_price_in_currency
