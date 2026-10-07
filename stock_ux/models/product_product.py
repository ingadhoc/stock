##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import statistics

from odoo import _, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def get_product_rotation(self, location=False, compute_stdev=False):
        self.ensure_one()
        # we should use cache for this date
        from_date = fields.Datetime.subtract(fields.Datetime.now(self), days=120)
        base_domain = [
            ("date", ">=", from_date),
            ("state", "=", "done"),
            ("product_id", "=", self.id),
        ]
        base_domain_send = base_domain + [("location_dest_id.usage", "=", "customer")]
        base_domain_return = base_domain + [("location_id.usage", "=", "customer")]

        if location:
            base_domain_send += [("location_id", "child_of", location.id)]
            base_domain_return += [("location_dest_id", "child_of", location.id)]

        quantities = self.env["stock.move"].search(base_domain_send).mapped("product_qty") + self.env[
            "stock.move"
        ].search(base_domain_return).mapped(lambda x: -x.product_qty)
        rotation = sum(quantities) / 4.0
        if compute_stdev:
            stdev = len(quantities) > 1 and statistics.stdev(quantities) or 0.0
            return rotation, stdev
        return rotation

    def action_view_stock_move(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.stock_move_action")
        action["domain"] = [("product_id", "=", self.id)]
        action["context"] = {
            "search_default_product_id": self.id,
            "default_product_id": self.id,
        }
        return action

    def action_archive(self):
        warning = self.filtered("active")._get_archive_stock_warning()
        res = super().action_archive()
        return self._archive_warning_action(warning, res)

    def _get_archive_stock_warning(self):
        """Warn about storable products that still have stock or pending moves."""
        storables = self.filtered("is_storable")
        if not storables:
            return False
        # Archiving is global, so look beyond the user's companies.
        with_stock = (
            self.env["stock.quant"]
            .sudo()
            .search(
                [
                    ("product_id", "in", storables.ids),
                    ("location_id.usage", "in", ("internal", "transit")),
                    ("quantity", "!=", 0),
                ]
            )
            .product_id
        )
        with_moves = (
            self.env["stock.move"]
            .sudo()
            .search(
                [
                    ("product_id", "in", storables.ids),
                    ("state", "not in", ("done", "cancel")),
                ]
            )
            .product_id
        )
        lines = []
        if with_stock:
            lines.append(_("With stock in internal or transit locations: %s", self._archive_names(with_stock)))
        if with_moves:
            lines.append(_("With pending inventory moves: %s", self._archive_names(with_moves)))
        return " ".join(lines)

    def _archive_names(self, products, limit=5):
        names = ", ".join(products[:limit].with_env(self.env).mapped("display_name"))
        if len(products) > limit:
            return _("%(names)s and %(count)s more", names=names, count=len(products) - limit)
        return names

    def _archive_warning_action(self, warning, res):
        if not warning:
            return res
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Products archived with stock or pending moves"),
                "message": warning,
                "type": "warning",
                "sticky": True,
                "next": res or {"type": "ir.actions.act_window_close"},
            },
        }
