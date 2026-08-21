from collections import defaultdict

from odoo import models
from odoo.fields import Domain


class ResCompany(models.Model):
    _inherit = "res.company"

    def stock_value_in_currency(self, accounts_by_product=None, at_date=None):
        """Inventory value per ``(valuation account, secondary currency)``.

        Twin of ``stock_value``, which answers the same in company currency. Keyed by
        currency as well because one valuation account can gather products valued in
        different secondary currencies; products without one contribute nothing.
        """
        self.ensure_one()
        value_by_account = defaultdict(float)
        if not accounts_by_product:
            accounts_by_product = self.with_context(prefetch_fields=False)._get_accounts_by_product()
        for product, accounts in accounts_by_product.items():
            scoped = product.with_company(self)
            currency = scoped.valuation_currency_id
            if not currency:
                continue
            value_by_account[accounts["valuation"], currency] += scoped.with_context(
                to_date=at_date
            ).total_value_in_currency
        return value_by_account

    def stock_accounting_value_in_currency(self, accounts_by_product=None, at_date=None):
        """Booked value per ``(valuation account, secondary currency)``, off the
        ``amount_currency`` of the posted journal items.

        Twin of ``stock_accounting_value``. It only sees what was booked WITH a secondary
        amount, so entries posted before this module did carry none and contribute zero —
        the column is not retroactive, and that is documented rather than estimated.

        Lines expressed in the company currency are left out on purpose: their
        ``amount_currency`` mirrors the balance and adding it would double the company
        figure into a secondary total.
        """
        self.ensure_one()
        if not accounts_by_product:
            accounts_by_product = self._get_accounts_by_product()
        account_data = defaultdict(float)
        currencies = self.env["res.currency"]
        accounts = self.env["account.account"]
        for product, product_accounts in accounts_by_product.items():
            currency = product.with_company(self).valuation_currency_id
            if not currency:
                continue
            currencies |= currency
            accounts |= product_accounts["valuation"]
        if not (currencies and accounts):
            return account_data
        domain = Domain(
            [
                ("account_id", "in", accounts.ids),
                ("company_id", "=", self.id),
                ("parent_state", "=", "posted"),
                ("currency_id", "in", currencies.ids),
            ]
        )
        if at_date:
            domain &= Domain([("date", "<=", at_date)])
        grouped = self.env["account.move.line"]._read_group(
            domain, ["account_id", "currency_id"], ["amount_currency:sum"]
        )
        for account, currency, amount in grouped:
            account_data[account, currency] += amount
        return account_data

    def _get_valuation_currency_by_account(self, accounts_by_product):
        """The single secondary currency of each valuation account, or nothing.

        A journal item carries ONE currency, so an account gathering products valued in
        different secondary currencies cannot state them all. Rather than pick one and be
        wrong, such an account is left out and its closing line stays in company currency
        — the same "one or none" rule the valuation wizard applies to its draft.

        Products with NO secondary currency disqualify the account just the same, and that
        is the common case rather than the exotic one: a category is valued in a second
        currency while the rest of the catalogue, on the same default valuation account,
        is not. The closing line of an account is split into one line per product and the
        secondary amount is shared out across ALL of them, so those products take a slice
        of an amount that is not theirs and the one actually valued in that currency is
        left with a fraction of its own value. Measured on a database with demo data: of
        100 in secondary currency belonging to a single product, that product kept 14,49
        and the rest went to a dozen furniture products valued in no second currency at
        all. An account that mixes them cannot be stated in one currency, so it stays in
        company currency until it holds only products valued in the same one — in
        practice, giving the category its own valuation account.
        """
        currencies_by_account = defaultdict(lambda: self.env["res.currency"])
        mixed_accounts = self.env["account.account"]
        for product, accounts in accounts_by_product.items():
            currency = product.with_company(self).valuation_currency_id
            if currency:
                currencies_by_account[accounts["valuation"]] |= currency
            else:
                mixed_accounts |= accounts["valuation"]
        return {
            account: currencies
            for account, currencies in currencies_by_account.items()
            if len(currencies) == 1 and account not in mixed_accounts
        }

    def _annotate_valuation_vals(self, vals_list, accounts_by_product, at_date=None):
        """Put the secondary amount on the closing vals, before they are split per product.

        The variation being booked is inventory value minus what is already booked, the
        same shape ``_get_stock_valuation_account_vals`` uses in company currency. The
        location-reclassification ``extra_balance`` is NOT netted here: it is a
        company-currency notion today, with no secondary twin, so netting it would mix
        units.

        Each pair of vals carries the amount with the sign of its own leg, so the entry
        adds up to zero in the secondary currency too. ``_get_valuation_val_extra_vals``
        prorates it afterwards when the line is split per product.
        """
        vals_list = super()._annotate_valuation_vals(vals_list, accounts_by_product, at_date=at_date)
        if not vals_list:
            return vals_list
        currency_by_account = self._get_valuation_currency_by_account(accounts_by_product)
        if not currency_by_account:
            return vals_list
        inventory = self.stock_value_in_currency(accounts_by_product, at_date)
        booked = self.stock_accounting_value_in_currency(accounts_by_product, at_date)
        Account = self.env["account.account"]
        # Walked TWO BY TWO: the vals come as pairs —valuation leg plus counterpart, as
        # ``_prepare_inventory_aml_vals`` returns them— and BOTH have to be annotated.
        # Annotating only the valuation leg moves it to the secondary currency and leaves
        # its counterpart alone in the company one, so neither group adds up to zero.
        for first, second in zip(vals_list[0::2], vals_list[1::2]):
            legs = {}
            for vals in (first, second):
                account = Account.browse(vals["account_id"])
                if account in currency_by_account:
                    legs[account] = vals
            # A pair that cannot be told apart is left alone rather than annotated wrongly:
            # an odd tail, or both legs being valuation accounts (one account's counterpart
            # is another product's valuation account).
            if len(legs) != 1:
                continue
            account = next(iter(legs))
            currency = currency_by_account[account]
            balance_in_currency = inventory.get((account, currency), 0.0) - booked.get((account, currency), 0.0)
            if currency.is_zero(balance_in_currency):
                continue
            amount = abs(balance_in_currency)
            for vals in (first, second):
                # Each leg carries the amount with the sign of its own balance, so the pair
                # nets to zero in the secondary currency exactly as it does in the company
                # one.
                vals["currency_id"] = currency.id
                vals["amount_currency"] = amount if vals["debit"] else -amount
        return vals_list

    def _get_valuation_val_extra_vals(self, vals, balance, net):
        """Prorate the secondary amount with the SAME denominator as the balance.

        Only ``debit`` / ``credit`` are re-split by the base, and every other key is copied
        verbatim onto every product line — right for the account or the label, wrong for an
        amount: N lines would each carry the full secondary amount, the entry would still
        add up in company currency, and would not in the other one.

        Left unrounded on purpose: ``_balance_valuation_extra_vals`` rounds the whole split
        at once, which is the only place the cent lost between the shares can be seen.
        """
        res = super()._get_valuation_val_extra_vals(vals, balance, net)
        if vals.get("amount_currency") and net:
            res["amount_currency"] = vals["amount_currency"] * balance / net
        return res

    def _balance_valuation_extra_vals(self, vals, product_vals):
        """Round every share and give the leftover to the largest one, so the split adds up
        to the secondary amount of the line it came from, to the cent.

        Rounding each share on its own leaves the entry off by a cent in the secondary
        currency —three products sharing 100 take 33,33 each and 0,01 goes missing— and
        nothing downstream catches it: the entry balances in company currency, so it posts.
        The leftover goes to the largest share because that is where it is worth least in
        relative terms.
        """
        product_vals = super()._balance_valuation_extra_vals(vals, product_vals)
        amount_currency = vals.get("amount_currency")
        currency = self.env["res.currency"].browse(vals.get("currency_id"))
        if not (amount_currency and currency):
            return product_vals
        shares = [share for share in product_vals if share.get("amount_currency")]
        if not shares:
            return product_vals
        for share in shares:
            share["amount_currency"] = currency.round(share["amount_currency"])
        leftover = currency.round(amount_currency - sum(share["amount_currency"] for share in shares))
        if not currency.is_zero(leftover):
            largest = max(shares, key=lambda share: abs(share["amount_currency"]))
            largest["amount_currency"] = currency.round(largest["amount_currency"] + leftover)
        return product_vals
