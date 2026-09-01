##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, api, models
from odoo.exceptions import UserError, ValidationError


class StockQuant(models.Model):
    _inherit = "stock.quant"

    def _is_inventory_mode(self):
        """Inventory adjustments are no longer granted by being a plain
        Inventory User. The "inventory session" mode (the one that creates the
        stock.move backing an adjustment) now requires the dedicated
        ``group_stock_inventory_adjustment`` group, so an Inventory User
        without it cannot apply adjustments even if it reaches an editable
        quant view."""
        return self.env.context.get("inventory_mode") and self.env.user.has_group(
            "stock_ux.group_stock_inventory_adjustment"
        )

    # ------------------------------------------------------------------
    # Actionable messages: name the offending column, product or line so the
    # importer points at the row instead of collapsing into "multiple rows"
    # ------------------------------------------------------------------

    def load(self, fields, data):
        """An inventory adjustment only takes the counted quantity and the columns that
        identify the stock line. Core answers a column it cannot take with a message that
        names none of them, and lets the on hand quantity through on the update path,
        moving stock with no move behind it."""
        if self.env.context.get("import_file"):
            wrong = self._get_non_importable_columns(fields)
            if wrong:
                return self._import_refused(
                    _(
                        'The column "%(columns)s" cannot be imported into an inventory '
                        "adjustment: it only takes the counted quantity and the columns "
                        "identifying the stock line. Remove it from the file.",
                        columns='", "'.join(wrong.values()),
                    )
                )
            guessed = self._get_guessed_import_location(fields)
            if guessed:
                return self._import_refused(
                    _(
                        "The file does not say where the count was taken and there is more "
                        "than one warehouse to take it in, so every row would land in "
                        '"%(location)s". Add the location column, or the column that '
                        "identifies each stock line.",
                        location=guessed.display_name,
                    )
                )
        return super().load(fields, data)

    def _import_refused(self, message):
        """A file that cannot be imported as it stands, answered the way load() answers."""
        return {"ids": False, "messages": [{"type": "error", "message": message}], "nextrow": 0}

    def _get_guessed_import_location(self, field_paths):
        """The location every row would land in when the file names none, and there is more
        than one to choose from. A count taken in the wrong warehouse reads as real stock."""
        names = [path.split("/")[0] for path in field_paths]
        if {"location_id", "id", ".id"} & set(names):
            return self.env["stock.location"]
        warehouses = self.env["stock.warehouse"].search([("company_id", "=", self.env.company.id)])
        if len(warehouses) < 2:
            return self.env["stock.location"]
        return warehouses[0].lot_stock_id

    def _get_non_importable_columns(self, field_paths):
        """Columns of the file that an inventory adjustment cannot take, by label."""
        names = [path.split("/")[0] for path in field_paths]
        allowed = self._get_inventory_fields_create() + ["id", ".id"]
        wrong = [name for name in names if name not in allowed and not name.startswith("x_")]
        if not wrong:
            # fields_get() answers an empty list with every field of the model
            return {}
        return {name: values["string"] for name, values in self.fields_get(wrong, ["string"]).items()}

    def write(self, vals):
        """A key field repeating the value the quant already has is not an edit: every file
        built from an export carries those columns. Only a different value is refused, and
        it says which line and which column disagree."""
        forbidden = [f for f in self._get_forbidden_fields_write() if f in vals]
        if (
            forbidden
            and self._is_inventory_mode()
            and not any(quant.location_id.usage == "inventory" for quant in self)
        ):
            for quant in self:
                conflicting = [f for f in forbidden if quant[f].id != (vals[f] or False)]
                if conflicting:
                    field = conflicting[0]
                    raise UserError(
                        _(
                            'The stock line "%(quant)s" cannot be moved to another '
                            '"%(field)s" from a file: it holds "%(current)s" and the file '
                            'brings "%(new)s". Product, location, lot, package and owner '
                            "identify the line: fix that row or drop the column.",
                            quant=quant.sudo().display_name,
                            field=self.fields_get([field], ["string"])[field]["string"],
                            current=quant.sudo()[field].display_name or _("empty"),
                            new=self.env[self._fields[field].comodel_name].browse(vals[field]).sudo().display_name
                            or _("empty"),
                        )
                    )
            vals = {k: v for k, v in vals.items() if k not in forbidden}
        return super().write(vals)

    @api.constrains("product_id")
    def check_product_id(self):
        """Same guard as core, naming the products and the real cause: inventory tracking."""
        wrong = self.filtered(lambda quant: not quant.product_id.is_storable)
        if wrong:
            raise ValidationError(
                _(
                    'The product "%(products)s" does not track inventory, so it cannot hold '
                    'stock. Enable "Track Inventory" on the product or remove its rows from '
                    "the file.",
                    products='", "'.join(wrong.sudo().product_id.mapped("display_name")),
                )
            )
