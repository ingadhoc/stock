##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import statistics

from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _update_orderpoints_qty_to_order(self):
        """Mark the orderpoints of these products for recomputation of the stored qty_to_order_computed.

        Use it when the stock changes without touching the move state, date or demand, which are
        the only move fields the computation depends on.
        """
        products = self.filtered("is_storable")
        if not products:
            return
        products.invalidate_recordset(["qty_available", "virtual_available"])
        orderpoints = (
            self.env["stock.warehouse.orderpoint"]
            .sudo()
            .with_context(active_test=False)
            .search([("product_id", "in", products.ids)])
        )
        orderpoints.invalidate_recordset(["qty_forecast", "qty_to_order"])
        self.env.add_to_compute(orderpoints._fields["qty_to_order_computed"], orderpoints)

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
