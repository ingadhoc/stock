##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


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
    # Spreadsheet import: replace the counted quantity, never add it up
    # ------------------------------------------------------------------

    def _extract_records(self, field_paths, data, log=lambda a: None, limit=float("inf")):
        """An empty cell in a counted quantity column is not a count of zero: half a file
        counted is the ordinary file, and the rows left blank must stay untouched. The
        converter turns both an empty cell and a 0 into the same 0.0, so the difference
        can only be told here, while the rows are still the strings of the file."""
        records = super()._extract_records(field_paths, data, log=log, limit=limit)
        if not self.env.context.get("import_file"):
            return records
        return self._drop_blank_counts(records)

    def _drop_blank_counts(self, records):
        for record, extras in records:
            for name in ("inventory_quantity", "inventory_quantity_auto_apply"):
                if name in record and not str(record[name] or "").strip():
                    del record[name]
            yield record, extras

    def _is_import_counting(self):
        """Whether these rows are a count being imported by someone allowed to adjust."""
        return bool(self.env.context.get("import_file")) and bool(
            self.with_context(inventory_mode=True)._is_inventory_mode()
        )

    @api.model
    def _get_import_quant_key(self, product_id, location_id, lot_id, package_id, owner_id):
        """What identifies a stock line: two rows with this key are the same quant."""
        return (product_id, location_id, lot_id or False, package_id or False, owner_id or False)

    def _set_import_default_location(self, values):
        """Same default location core applies while importing, needed before the lookup so
        matching and creation agree on where the row lands."""
        warehouse = self.env["stock.warehouse"].search([("company_id", "=", self.env.company.id)], limit=1)
        for vals in values:
            if "location_id" not in vals:
                vals["location_id"] = warehouse.lot_stock_id.id

    def _normalize_import_lot(self, vals):
        """A lot name is only unique per product, so the importer may resolve it to another
        product's lot. Re-point it to this product's lot when it exists, as core does on
        creation, otherwise the lookup would miss and duplicate the line."""
        product = self.env["product.product"].browse(vals.get("product_id"))
        lot = self.env["stock.lot"].browse(vals.get("lot_id"))
        if product and lot and lot.product_id != product:
            lot = self.env["stock.lot"].search([("product_id", "=", product.id), ("name", "=", lot.name)], limit=1)
            if lot:
                vals["lot_id"] = lot.id

    def _index_import_quants(self, values):
        """The quants the imported rows may already hold, in a single search: a count of
        thousands of lines would otherwise search once per row."""
        products = {vals["product_id"] for vals in values if vals.get("product_id")}
        locations = {vals["location_id"] for vals in values if vals.get("location_id")}
        if not products or not locations:
            return {}
        # No sudo: a row can only land on a quant its author is allowed to see.
        quants = self.search(
            [("product_id", "in", list(products)), ("location_id", "in", list(locations))],
            order="in_date, id",
        )
        index = {}
        for quant in quants:
            key = self._get_import_quant_key(
                quant.product_id.id,
                quant.location_id.id,
                quant.lot_id.id,
                quant.package_id.id,
                quant.owner_id.id,
            )
            # A position holding more than one quant is what core's merge undoes: keep the
            # one it keeps.
            index.setdefault(key, quant)
        return index

    def _write_imported_quantity(self, quant, vals):
        """Apply an imported row on the quant it matched, the same way core applies it on
        the quant it gathers when it is not importing."""
        quant = quant.with_context(inventory_mode=True)
        if "inventory_quantity_auto_apply" in vals:
            quant.write({"inventory_quantity_auto_apply": vals.get("inventory_quantity_auto_apply") or 0})
        else:
            quant.write(
                {
                    "inventory_quantity": vals.get("inventory_quantity") or 0,
                    # a counted 0 on a line that was never counted writes no value, and an
                    # unset line shows no difference and stays out of "Apply all"
                    "inventory_quantity_set": True,
                    "user_id": vals.get("user_id") or self.env.user.id,
                    "inventory_date": vals.get("inventory_date") or fields.Date.today(),
                }
            )
        return quant

    def _load_records_create(self, values):
        """On import, write the counted quantity on the quant that already holds that
        product/location/lot/package/owner instead of adding a second line that sums up.
        Core skips that lookup while importing to keep one row = one record, an invariant
        this override must preserve: it returns exactly one record per row, in order."""
        if not self._is_import_counting():
            return super()._load_records_create(values)
        self._set_import_default_location(values)
        for vals in values:
            self._normalize_import_lot(vals)
        index = self._index_import_quants(values)
        records = [None] * len(values)
        pending = {}
        for position, vals in enumerate(values):
            # A row carrying no count is not a count: writing a 0 on the line it names
            # would empty stock nobody asked to empty.
            counted = any(f in vals for f in ("inventory_quantity", "inventory_quantity_auto_apply"))
            key = self._get_import_quant_key(
                vals.get("product_id"),
                vals.get("location_id"),
                vals.get("lot_id"),
                vals.get("package_id"),
                vals.get("owner_id"),
            )
            quant = index.get(key) if vals.get("product_id") else None
            if quant:
                # A row that names a line without counting it says nothing about it.
                records[position] = self._write_imported_quantity(quant, vals) if counted else quant
                continue
            # Rows sharing a key are the same line, so the last count wins, as it would
            # if the first of them had already created that line.
            group = key if counted and vals.get("product_id") else ("row", position)
            entry = pending.setdefault(group, {"positions": []})
            entry["positions"].append(position)
            entry["vals"] = vals
        if pending:
            created = super()._load_records_create([entry["vals"] for entry in pending.values()])
            for entry, record in zip(pending.values(), created):
                for position in entry["positions"]:
                    records[position] = record
        return self.browse(tuple(record.id for record in records))
