from collections import defaultdict

from odoo import api, fields, models
from odoo.fields import Domain


class StockMove(models.Model):
    _inherit = "stock.move"

    valuation_currency_id = fields.Many2one(
        related="product_id.valuation_currency_id",
    )
    value_in_currency = fields.Monetary(
        "Currency Value",
        currency_field="valuation_currency_id",
        help="The current value of the move. It's zero if the move is not valued.",
    )
    value_manual_in_currency = fields.Monetary(
        "Currency Manual Value",
        currency_field="valuation_currency_id",
        compute="_compute_value_manual",
        inverse="_inverse_value_in_currency_manual",
    )
    standard_price_in_currency = fields.Float(
        compute="_compute_standard_price_in_currency",
    )

    @api.depends("product_id.standard_price_in_currency")
    def _compute_standard_price_in_currency(self):
        for move in self:
            move.standard_price_in_currency = move.product_id.with_company(move.company_id).standard_price_in_currency

    def _inverse_value_in_currency_manual(self):
        for move in self:
            if move.value_manual_in_currency == move.value_in_currency:
                continue
            self.env["product.value"].create(
                {
                    "move_id": move.id,
                    "value_in_currency": move.value_manual_in_currency,
                    "company_id": move.company_id.id,
                }
            )

    def _compute_value_manual(self):
        super()._compute_value_manual()
        for move in self:
            move.value_manual_in_currency = move.value_in_currency

    def _get_inventory_value_in_currency(self):
        """What the move contributes to the inventory valuation IN THE SECONDARY currency.

        Twin of ``stock.move._get_inventory_value``, which answers the same in company
        currency. Single home of the criterion, so the wizard that books selected moves
        and the report's breakdown of the variation measure the same thing instead of each
        deciding on its own.

        It is ``value_in_currency`` and not a recomputation on purpose: that field already
        holds the move's valuation in force, manual adjustments included (see
        ``_get_manual_value_in_currency``). Recomputing here would ignore a correction the
        user made by hand. A move whose category has no secondary currency contributes
        zero, which is what the field holds.
        """
        self.ensure_one()
        return self.value_in_currency

    def _get_manual_value_in_currency(self, at_date=None):
        """Manual override of this move's value in the secondary currency, or ``None``.

        Mirror of the core's ``_get_manual_value``, which does the same for the company
        currency: same lookup —the move's most recent ``product.value``— reading the other
        amount off it. ``None`` and not ``0`` marks "no adjustment", so an explicit zero
        (a manual correction down to nothing) is honoured instead of being read as absence.
        """
        self.ensure_one()
        domain = Domain([("move_id", "=", self.id)])
        if at_date:
            domain &= Domain([("date", "<=", at_date)])
        adjustment = self.env["product.value"].sudo().search(domain, order="date desc, id desc", limit=1)
        return adjustment.value_in_currency if adjustment else None

    def _set_value(self, correction_quantity=None):
        # AVCO en moneda secundaria ANTES de que super() dispare _update_standard_price.
        # Los OUT (con o sin picking) y los ajustes de entrada sin picking valúan
        # value_in_currency a este AVCO; capturamos el valor previo para que, si ese
        # mismo recálculo dispara _update_standard_price, no se use el promedio ya
        # degradado por este move.
        std_price_in_currency_before = {
            move.product_id.id: move.product_id.with_company(move.company_id).standard_price_in_currency
            for move in self
            if move.with_company(move.company_id).valuation_currency_id
        }
        super()._set_value(correction_quantity=correction_quantity)
        # Agrupado por compañía (no un set plano): el core recompute standard_price con
        # with_company(company) de cada move (ver stock_account._set_value), porque
        # self.env.company puede no coincidir con move.company_id (batch multi-compañía,
        # jobs automatizados). Mezclarlos filtraría/recomputaría con la compañía equivocada.
        products_to_recompute_by_company = defaultdict(set)

        # sudo: stock.valuation.adjustment.lines sólo es legible por
        # stock.group_stock_manager, pero este cómputo interno de valuación
        # corre para cualquier usuario que valide un move (p.ej. flujos de caja).
        landed_costs_by_move = self.sudo()._get_landed_cost()

        for move in self:
            if move.with_company(move.company_id).valuation_currency_id and move.value:
                if move.is_dropship or move.is_in:
                    products_to_recompute_by_company[move.company_id.id].add(move.product_id.id)

                lcs = landed_costs_by_move.get(move, self.env["stock.valuation.adjustment.lines"])
                lc_value = sum(lcs.mapped("additional_landed_cost"))
                lc_value_in_currency = sum(lcs.mapped("additional_landed_cost_in_currency"))
                base_value = move.value - lc_value

                # Un ajuste manual del importe en moneda tiene PRIORIDAD sobre el cálculo,
                # igual que en el core el _get_manual_value la tiene sobre factura,
                # cotización y costo (ver stock.move._get_value_data). Sin esto el campo
                # que el diálogo "Adjust Valuation" expone como "New Value in Currency"
                # escribía un registro que nadie leía: acá abajo value_in_currency se
                # recalculaba siempre desde el AVCO o la cotización del remito.
                manual_value_in_currency = move._get_manual_value_in_currency()
                if manual_value_in_currency is not None:
                    move.value_in_currency = manual_value_in_currency
                    continue

                # move.is_out es un campo stored que sólo se recomputa con state=='done',
                # pero _set_value() de los OUT corre ANTES de que action_done marque ese
                # estado (ver core: `moves_out = self.filtered(lambda m: m._is_out())`,
                # usa el método, no el campo). Por eso acá también usamos el método.
                if move._is_out() or not move.picking_id:
                    # OUT (entregas, devoluciones a proveedor, etc.) y ajustes sin picking
                    # (inventario, scrap, producción): se valúan siempre al AVCO en moneda
                    # secundaria vigente (standard_price_in_currency previo a este move),
                    # igual que el core los valúa al standard_price en moneda de compañía.
                    # Esto preserva el promedio. Magnitud positiva, en línea con la
                    # convención de signo de move.value.
                    # Nota: no se suma lc_value_in_currency acá — el core nunca incorpora
                    # landed costs a move.value en OUT (_get_value_from_extra sólo se usa
                    # para IN), así que sumarlo acá rompería la paridad y el invariante
                    # "OUT preserva el AVCO" (ver stock.landed.cost.picking_ids: un LC puede
                    # linkearse a un move OUT sin restricción de dirección).
                    std_price_in_currency = std_price_in_currency_before.get(move.product_id.id, 0)
                    base_value_in_currency = move._get_valued_qty() * std_price_in_currency
                    move.value_in_currency = base_value_in_currency
                elif move.picking_id.currency_rate:
                    base_value_in_currency = base_value * move.picking_id.currency_rate
                    move.value_in_currency = base_value_in_currency + lc_value_in_currency
                else:
                    # ``valuation_currency_id`` comes from the product category and is
                    # company-dependent: resolved off the move's own company, not the
                    # ambient one, which can be another company entirely under
                    # account_multicompany_ux.
                    move_in_company = move.with_company(move.company_id)
                    base_value_in_currency = move_in_company.company_id.currency_id._convert(
                        from_amount=base_value,
                        to_currency=move_in_company.valuation_currency_id,
                        company=move.company_id,
                        date=move.date,
                    )
                    move.value_in_currency = base_value_in_currency + lc_value_in_currency

<<<<<<< 9ad1dda987a83a88d6b2f238fac535577951133b
        # Recompute the standard price, con la compañía de cada move (no la ambiente)
        for company_id, product_ids in products_to_recompute_by_company.items():
            self.env["product.product"].browse(product_ids).with_company(company_id)._update_standard_price()
||||||| 8c94b5858668ed8ed261987e7ad767f5caa1beb5
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
            product_with_company = move.product_id.with_company(move.company_id)
            product_tot_qty_available = product_with_company.sudo().quantity_svl + tmpl_dict[move.product_id.id]
            rounding = product_with_company.uom_id.rounding

            valued_move_lines = move._get_in_move_lines()
            qty_done = 0
            for valued_move_line in valued_move_lines:
                qty_done += valued_move_line.product_uom_id._compute_quantity(
                    valued_move_line.qty_done, product_with_company.uom_id
                )

            qty = forced_qty or qty_done
            if float_is_zero(product_tot_qty_available, precision_rounding=rounding):
                new_std_price_in_currency = move._get_currency_price_unit(
                    default=product_with_company.standard_price_in_currency
                )
            elif float_is_zero(
                product_tot_qty_available + move.product_qty, precision_rounding=rounding
            ) or float_is_zero(product_tot_qty_available + qty, precision_rounding=rounding):
                new_std_price_in_currency = move._get_currency_price_unit(
                    default=product_with_company.standard_price_in_currency
                )
            else:
                # Get the standard price
                amount_unit = (
                    std_price_update.get((move.company_id.id, move.product_id.id))
                    or product_with_company.standard_price_in_currency
                )
                new_std_price_in_currency = (
                    (amount_unit * product_tot_qty_available) + (move._get_currency_price_unit() * qty)
                ) / (product_tot_qty_available + qty)

            tmpl_dict[move.product_id.id] += qty_done
            # Write the standard price, as SUPERUSER_ID because a warehouse manager may not have the right to write on products
            product_with_company.with_context(disable_auto_svl=True).sudo().write(
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

        if (
            self.picking_id.currency_rate
            and self.purchase_line_id
            and self.purchase_line_id.order_id.currency_id == self.picking_id.valuation_currency_id
        ):
            # When a custom currency_rate is set on the picking, use the PO line
            # price directly in secondary currency (already UoM-converted by
            # _get_gross_price_unit), so the AVCO update is consistent with the SVL.
            price_unit = self.purchase_line_id._get_gross_price_unit()
        else:
            price_unit = currency_id._convert(
                from_amount=self.price_unit,
                to_currency=self.product_id.with_company(self.company_id.id).categ_id.valuation_currency_id,
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
=======
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
            product_with_company = move.product_id.with_company(move.company_id)
            product_tot_qty_available = product_with_company.sudo().quantity_svl + tmpl_dict[move.product_id.id]
            rounding = product_with_company.uom_id.rounding

            valued_move_lines = move._get_in_move_lines()
            qty_done = 0
            for valued_move_line in valued_move_lines:
                qty_done += valued_move_line.product_uom_id._compute_quantity(
                    valued_move_line.qty_done, product_with_company.uom_id
                )

            qty = forced_qty or qty_done
            if float_is_zero(product_tot_qty_available, precision_rounding=rounding):
                new_std_price_in_currency = move._get_currency_price_unit(
                    default=product_with_company.standard_price_in_currency
                )
            elif float_is_zero(
                product_tot_qty_available + move.product_qty, precision_rounding=rounding
            ) or float_is_zero(product_tot_qty_available + qty, precision_rounding=rounding):
                new_std_price_in_currency = move._get_currency_price_unit(
                    default=product_with_company.standard_price_in_currency
                )
            else:
                # Get the standard price
                amount_unit = (
                    std_price_update.get((move.company_id.id, move.product_id.id))
                    or product_with_company.standard_price_in_currency
                )
                new_std_price_in_currency = (
                    (amount_unit * product_tot_qty_available) + (move._get_currency_price_unit() * qty)
                ) / (product_tot_qty_available + qty)

            tmpl_dict[move.product_id.id] += qty_done
            # Write the standard price, as SUPERUSER_ID because a warehouse manager may not have the right to write on products
            product_with_company.with_context(disable_auto_svl=True).sudo().write(
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

        if (
            self.picking_id.currency_rate
            and self.purchase_line_id
            and self.purchase_line_id.order_id.currency_id == self.picking_id.valuation_currency_id
        ):
            # When a custom currency_rate is set on the picking, use the PO line
            # price directly in secondary currency (already UoM-converted by
            # _get_gross_price_unit), so the AVCO update is consistent with the SVL.
            price_unit = self.purchase_line_id._get_gross_price_unit()
        else:
            price_unit = currency_id._convert(
                from_amount=self.price_unit,
                to_currency=self.product_id.with_company(self.company_id.id).categ_id.valuation_currency_id,
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
        # Like purchase_stock does in company currency, a purchase line price is used as is, even when it is zero.
        if (
            float_is_zero(price_unit, precision)
            and not self._should_force_price_unit()
            and self._should_ignore_pol_price()
        ):
            return default
        return price_unit
>>>>>>> 708a2b90c2f124e8dc8919a2d87d6643880f7cf9
