from collections import defaultdict

from odoo import api, fields, models


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
                    base_value_in_currency = move.with_company(move.company_id).company_id.currency_id._convert(
                        from_amount=base_value,
                        to_currency=move.valuation_currency_id,
                        company=move.company_id,
                        date=move.date,
                    )
                    move.value_in_currency = base_value_in_currency + lc_value_in_currency

        # Recompute the standard price, con la compañía de cada move (no la ambiente)
        for company_id, product_ids in products_to_recompute_by_company.items():
            self.env["product.product"].browse(product_ids).with_company(company_id)._update_standard_price()
