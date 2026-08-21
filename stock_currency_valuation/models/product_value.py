from odoo import api, fields, models


class ProductValue(models.Model):
    _inherit = "product.value"

    valuation_currency_id = fields.Many2one("res.currency", compute="_compute_valuation_currency_id", store=True)
    value_in_currency = fields.Monetary(string="Value in Currency", currency_field="valuation_currency_id")
    previous_value_in_currency = fields.Monetary(
        string="Previous Value in Currency",
        currency_field="valuation_currency_id",
        readonly=True,
        copy=False,
        help="Value in the secondary currency in force right before this adjustment. "
        "Captured when it is recorded, because afterwards it can no longer be rebuilt.",
    )
    delta_in_currency = fields.Monetary(
        string="Delta in Currency",
        currency_field="valuation_currency_id",
        compute="_compute_delta_in_currency",
        help="Variation this adjustment introduced in the secondary currency, in the SAME "
        "unit as the Value in Currency field: the move total when the adjustment is on a "
        "move, the unit price when it is a product or lot price change.",
    )

    @api.depends("value_in_currency", "previous_value_in_currency")
    def _compute_delta_in_currency(self):
        """Twin of ``delta`` in the secondary currency. Same reason for keeping a captured
        ``previous_value_in_currency`` instead of deriving it: once the record is saved the
        adjustment has already been applied, so there is nothing left to subtract from."""
        for product_value in self:
            product_value.delta_in_currency = product_value.value_in_currency - product_value.previous_value_in_currency

    @api.depends("company_id", "move_id", "lot_id", "product_id")
    def _compute_valuation_currency_id(self):
        for product_value in self:
            if product_value.move_id:
                product_value.valuation_currency_id = product_value.move_id.product_id.with_company(
                    product_value.company_id
                ).valuation_currency_id.id
            elif product_value.lot_id:
                product_value.valuation_currency_id = product_value.lot_id.product_id.with_company(
                    product_value.company_id
                ).valuation_currency_id.id
            elif product_value.product_id:
                product_value.valuation_currency_id = product_value.product_id.with_company(
                    product_value.company_id
                ).valuation_currency_id.id

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set default values from product's standard_price if not provided"""
        for vals in vals_list:
            # Obtener el producto según el contexto
            product = None
            move = self.env["stock.move"]
            if vals.get("product_id"):
                product = self.env["product.product"].browse(vals["product_id"])
            elif vals.get("lot_id"):
                lot = self.env["stock.lot"].browse(vals["lot_id"])
                product = lot.product_id
            elif vals.get("move_id"):
                move = self.env["stock.move"].browse(vals["move_id"])
                product = move.product_id

            if product:
                # Obtener la compañía
                company_id = vals.get("company_id")
                if not company_id:
                    if vals.get("move_id"):
                        company_id = self.env["stock.move"].browse(vals["move_id"]).company_id.id
                    elif vals.get("lot_id"):
                        company_id = self.env["stock.lot"].browse(vals["lot_id"]).company_id.id
                    else:
                        company_id = self.env.company.id

                company = self.env["res.company"].browse(company_id)
                product_with_company = product.with_company(company)

                # Si no está definido value, tomar el default que corresponde al TIPO de
                # ajuste. Sobre un movimiento, ``value`` es el valor TOTAL del movimiento y
                # no un precio unitario (ver el docstring del modelo en stock_account, y
                # ``stock.move._get_manual_value``, que lo escribe derecho en
                # ``move.value``): defaultearlo al standard_price ponía un precio unitario
                # donde va un total y dejaba el movimiento valuado al costo de una unidad.
                # Sólo un cambio de precio de producto o lote defaultea al standard_price.
                #
                # Ojo: chequear sólo ausencia de la clave, no falsy — un 0 explícito
                # (p.ej. una corrección manual a cero vía value_manual) es un valor
                # válido y no debe pisarse.
                if "value" not in vals:
                    vals["value"] = move.value if move else product_with_company.standard_price

                # Idem para value_in_currency, con el mismo criterio por tipo de ajuste.
                if "value_in_currency" not in vals and product_with_company.valuation_currency_id:
                    vals["value_in_currency"] = (
                        move.value_in_currency if move else product_with_company.standard_price_in_currency
                    )
        # Igual que el previous_value en moneda de compañía: se resuelve ANTES de delegar,
        # porque el create del core dispara _set_value() / _update_standard_price() y deja
        # el valor nuevo tanto en el movimiento como en el producto.
        vals_list = [
            vals
            if "previous_value_in_currency" in vals
            else dict(vals, previous_value_in_currency=self._get_previous_value_in_currency(vals))
            for vals in vals_list
        ]
        return super().create(vals_list)

    @api.model
    def _get_previous_value_in_currency(self, vals):
        """Secondary-currency twin of ``product.value._get_previous_value``.

        For a price change it reads the amount off the RECORD that
        ``_get_previous_product_value`` returns, which is what that seam exists for (task
        58212): the company scope and the date bound of that search are not repeated here.
        For an adjustment on a move the previous value is the move's own, as there is no
        earlier adjustment to read it off.
        """
        if vals.get("move_id"):
            return self.env["stock.move"].browse(vals["move_id"]).value_in_currency
        return self._get_previous_product_value(vals).value_in_currency
