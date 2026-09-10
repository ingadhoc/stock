##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


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
    # Spreadsheet import: lots the count brings and Odoo does not have yet
    # ------------------------------------------------------------------

    @api.model
    def _convert_records(self, records, *, log=lambda a: None, savepoint):
        """Create the lots the count names before the importer tries to resolve them:
        counting a warehouse routinely turns up lots that are new to Odoo, and a single
        one of them stops the whole file."""
        if self.env.context.get("import_file"):
            records = list(records)
            self._create_missing_import_lots(records)
        return super()._convert_records(records, log=log, savepoint=savepoint)

    @api.model
    def _get_import_name(self, value):
        """Name a row gives for a relational column, which the importer hands over as a
        sub-record. Anything referenced by id is left alone: it already exists."""
        if isinstance(value, list) and len(value) == 1 and isinstance(value[0], dict):
            name = value[0].get(None)
            return name.strip() if isinstance(name, str) else None
        return None

    def _create_missing_import_lots(self, records):
        """Lots named by a row whose product does not have them yet, created for that
        product so that the row resolves to a lot of its own product."""
        Product = self.env["product.product"]
        Location = self.env["stock.location"]
        resolved = {}

        def resolve(model, name):
            """Same lookup the importer does on a column given by name."""
            if (model._name, name) not in resolved:
                found = model.name_search(name=name, operator="=", limit=1)
                resolved[model._name, name] = model.browse(found[0][0]) if found else model
            return resolved[model._name, name]

        wanted = {}
        for record, _extras in records:
            lot_name = self._get_import_name(record.get("lot_id"))
            product_name = self._get_import_name(record.get("product_id"))
            if not lot_name or not product_name:
                continue
            product = resolve(Product, product_name)
            if not product or product.tracking == "none":
                continue
            location_name = self._get_import_name(record.get("location_id"))
            company = resolve(Location, location_name).company_id if location_name else False
            wanted[product.id, lot_name] = (company or self.env.company).id
        if not wanted:
            return
        Lot = self.env["stock.lot"]
        existing = Lot.search(
            [
                ("product_id", "in", [product_id for product_id, _name in wanted]),
                ("name", "in", [name for _product_id, name in wanted]),
            ]
        )
        for lot in existing:
            wanted.pop((lot.product_id.id, lot.name), None)
        Lot.create(
            [
                {"name": name, "product_id": product_id, "company_id": company_id}
                for (product_id, name), company_id in wanted.items()
            ]
        )
