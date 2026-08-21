from collections import defaultdict

from odoo import api, fields, models


class StockMoveValuation(models.TransientModel):
    _inherit = "stock.move.valuation"

    valuation_currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_valuation_currency_id",
        help="Secondary valuation currency of the draft, when every line shares one.",
    )
    total_in_currency = fields.Monetary(
        string="Total in Currency",
        currency_field="valuation_currency_id",
        compute="_compute_line_ids",
        help="Total of the entry to post, in the secondary valuation currency.",
    )

    def _compute_valuation_currency_id(self):
        """One currency only when ALL the lines share it.

        A single wizard can gather moves of products valued in different secondary
        currencies, and then a single total states nothing — so it is left empty and the
        view hides it, the same way ``stock.landed.cost`` resolves it in this module. The
        per-line amounts stay visible either way, since each line is one product.
        """
        for wizard in self:
            currencies = wizard.line_ids.valuation_currency_id
            wizard.valuation_currency_id = currencies if len(currencies) == 1 else False

    def _compute_line_ids(self):
        """Extends the base compute, which owns ``line_ids`` and ``total``, to also produce
        the total in the secondary currency. Mirrors the base criterion: the sum of the
        debit side, which is the entry's amount once."""
        super()._compute_line_ids()
        for wizard in self:
            wizard.total_in_currency = sum(line.amount_currency for line in wizard.line_ids if line.amount_currency > 0)

    def _get_draft_line_vals(self, aml_vals):
        """Carry the secondary amount onto the draft line, so the user sees before posting
        what the entry is going to say in the other currency."""
        vals = super()._get_draft_line_vals(aml_vals)
        if aml_vals.get("amount_currency"):
            vals["amount_currency"] = aml_vals["amount_currency"]
        return vals

    def _get_balances_by_accounts_in_currency(self):
        """Balance to book in the SECONDARY currency, keyed exactly like the one in company
        currency.

        Same grouping —so both dicts can be read side by side by key— and the same in/out
        sign rule. What a move contributes is ``_get_inventory_value_in_currency``, the
        twin of the criterion the base uses, so the two amounts of a line describe the same
        moves.
        """
        self.ensure_one()
        balances = defaultdict(float)
        accounts_by_product = {}
        for move in self.move_ids:
            product = move.product_id
            if product.id not in accounts_by_product:
                accounts_by_product[product.id] = product.with_company(self.company_id)._get_product_accounts()
            accounts = accounts_by_product[product.id]
            valuation_account = accounts.get("stock_valuation")
            if not valuation_account:
                continue
            counterpart = valuation_account.account_stock_variation_id or self.company_id.expense_account_id
            if not counterpart:
                continue
            value = move._get_inventory_value_in_currency()
            key = self._get_balance_key(move, valuation_account, counterpart)
            balances[key] += value if move.is_in else -value
        return balances

    def _get_aml_vals_for_key(self, key, balance):
        """Add the secondary-currency amount to the journal items of this key.

        ``_prepare_inventory_aml_vals`` swaps the legs when the balance is negative, so the
        sign of each line is read off its own ``debit`` / ``credit`` instead of being
        assumed: the valuation leg and its counterpart carry the amount with opposite
        signs, exactly as ``balance`` and its mirror do, so the entry adds up to zero in
        both currencies.
        """
        aml_vals = super()._get_aml_vals_for_key(key, balance)
        currency = self._get_key_valuation_currency(key)
        if not currency:
            return aml_vals
        balance_in_currency = self._get_balances_by_accounts_in_currency().get(key, 0.0)
        if currency.is_zero(balance_in_currency):
            return aml_vals
        # The company-currency balance tells which leg is which: the line whose ``debit``
        # matches its absolute value is the one carrying the same sign as ``balance``.
        for vals in aml_vals:
            same_sign_as_balance = bool(vals["debit"]) == (balance > 0)
            vals["currency_id"] = currency.id
            vals["amount_currency"] = balance_in_currency if same_sign_as_balance else -balance_in_currency
        return aml_vals

    def _get_key_valuation_currency(self, key):
        """Valuation currency of a grouped balance, taken off its product — the third slot
        of the key (see ``_get_balance_key``)."""
        product = key[2]
        return product.with_company(self.company_id).valuation_currency_id


class StockMoveValuationLine(models.TransientModel):
    _inherit = "stock.move.valuation.line"

    valuation_currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_valuation_currency_id",
    )
    amount_currency = fields.Monetary(
        string="Amount in Currency",
        currency_field="valuation_currency_id",
        readonly=True,
    )

    @api.depends("product_id", "valuation_id.company_id")
    def _compute_valuation_currency_id(self):
        """Resolved with the WIZARD's company and not the ambient one: the valuation
        currency lives on the product category and is company-dependent."""
        for line in self:
            line.valuation_currency_id = line.product_id.with_company(
                line.valuation_id.company_id
            ).valuation_currency_id
