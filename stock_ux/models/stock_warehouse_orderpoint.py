##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

import logging
from ast import literal_eval

from odoo import api, fields, models
from odoo.osv import expression
from odoo.tools import float_compare, float_is_zero

_logger = logging.getLogger(__name__)


class StockWarehouseOrderpoint(models.Model):
    _name = "stock.warehouse.orderpoint"
    _inherit = ["stock.warehouse.orderpoint", "mail.thread"]

    # Backport from v19: add index for better performance
    warehouse_id = fields.Many2one(index=True)

    active_product = fields.Boolean(string="Product Active", related="product_id.active")

    # Backport from v19: store qty_to_order_computed for better performance
    qty_to_order_computed = fields.Float(
        store=True,
    )

    rotation_stdev = fields.Float(
        compute="_compute_rotation",
        help="Desvío estandar de las cantidades entregas a clientes en los últimos 120 días.",
        digits="Product Unit of Measure",
    )
    warehouse_rotation_stdev = fields.Float(
        compute="_compute_rotation",
        help="Desvío estandar de las cantidades entregas desde este almacen a clientes en los últimos 120 días.",
        digits="Product Unit of Measure",
    )
    rotation = fields.Float(
        help="Cantidades entregadas a clientes en los "
        "últimos 120 días dividido por 4 para mensualizar "
        "(restadas devoluciones).",
        compute="_compute_rotation",
        digits="Product Unit of Measure",
    )
    warehouse_rotation = fields.Float(
        help="Cantidades entregadas desde este almacen a clientes en los "
        "últimos 120 días dividido por 4 para mensualizar"
        "(restadas devoluciones).",
        compute="_compute_rotation",
        digits="Product Unit of Measure",
    )
    product_min_qty = fields.Float(tracking=True)
    product_max_qty = fields.Float(tracking=True)
    qty_multiple = fields.Float(tracking=True)
    qty_multiple_over_max = fields.Selection(
        selection=[
            ("company", "Use Company Setting"),
            ("allow", "Allow Exceeding Max"),
            ("restrict", "Respect Max"),
        ],
        string="Multiple Above Max",
        default="company",
        required=True,
        tracking=True,
    )
    location_id = fields.Many2one(tracking=True)
    product_id = fields.Many2one(tracking=True)
    reviewed = fields.Boolean()

    # Backport from v19: updated depends for qty_to_order_computed
    # Note: qty_forecast depends on stock_move_ids which changes frequently.
    # We intentionally don't include it to avoid constant recomputation.
    # Instead, we rely on the explicit recomputation in _run_pull when moves are created.
    @api.depends(
        "qty_multiple",
        "product_min_qty",
        "product_max_qty",
        "visibility_days",
        "product_id",
        "location_id",
        "product_id.seller_ids.delay",
    )
    def _compute_qty_to_order_computed(self):
        """Extend to add more depends values.
        Backport from v19 to improve performance by storing computed qty_to_order.
        """
        return super()._compute_qty_to_order_computed()

    # Improved search method without filtered_domain
    def _search_qty_to_order(self, operator, value):
        """Search method for qty_to_order that avoids filtered_domain performance issues.

        This creates a more efficient domain that:
        1. For manual orderpoints: checks qty_to_order_manual directly
        2. For auto orderpoints: uses the stored qty_to_order_computed field
        3. Combines both with OR logic to avoid loading all records
        """
        # For manual orderpoints (with qty_to_order_manual != 0), check qty_to_order_manual
        manual_domain = [
            "&",
            ("qty_to_order_manual", "!=", 0),
            ("qty_to_order_manual", operator, value),
        ]

        # For auto orderpoints (qty_to_order_manual = 0), check computed value
        auto_domain = [
            "&",
            ("qty_to_order_manual", "=", 0),
            ("qty_to_order_computed", operator, value),
        ]

        # Return domain that combines both cases
        return ["|"] + manual_domain + auto_domain

    @api.depends("product_id", "location_id")
    def _compute_rotation(self):
        warehouse_with_products = self.filtered("product_id")
        (self - warehouse_with_products).update(
            {
                "rotation": 0.0,
                "rotation_stdev": 0.0,
                "warehouse_rotation_stdev": 0.0,
                "warehouse_rotation": 0.0,
            }
        )
        for rec in warehouse_with_products:
            rotation, rotation_stdev = rec.product_id.get_product_rotation(compute_stdev=True)
            warehouse_rotation, warehouse_rotation_stdev = rec.product_id.get_product_rotation(
                rec.warehouse_id.view_location_id, compute_stdev=True
            )
            rec.update(
                {
                    "rotation": rotation,
                    "rotation_stdev": rotation_stdev,
                    "warehouse_rotation_stdev": warehouse_rotation_stdev,
                    "warehouse_rotation": warehouse_rotation,
                }
            )

    def write(self, vals):
        """When archive a replenishment rule
        set min, max and multiple quantities in 0.
        """
        if "active" in vals and not vals["active"]:
            self.write(
                {
                    "product_min_qty": 0.0,
                    "product_max_qty": 0.0,
                    "qty_multiple": 0.0,
                }
            )
        return super().write(vals)

    def _get_orderpoint_action(self):
        action = super()._get_orderpoint_action()
        action["context"] = {
            **action["context"],
            "active_test": False,
        }
        existing_domain = action.get("domain") or []
        if isinstance(existing_domain, str):
            try:
                existing_domain = literal_eval(existing_domain)
            except (ValueError, SyntaxError) as e:
                _logger.warning("Failed to parse existing_domain with literal_eval: %s. Error: %s", existing_domain, e)
        action["domain"] = expression.AND(
            [
                existing_domain,
                [("active_product", "=", True)],
            ]
        )
        return action

    def _change_review_toggle_negative(self):
        self.reviewed = False

    @api.onchange("qty_to_order")
    def _change_review_toggle_positive(self):
        self.reviewed = True

    def action_replenish(self, force_to_max=False):
        # deactivate toggle after ordering
        self._change_review_toggle_negative()
        return super(StockWarehouseOrderpoint, self).action_replenish(force_to_max)

    def _is_qty_multiple_over_max_allowed(self):
        self.ensure_one()
        if self.qty_multiple_over_max == "allow":
            return True
        if self.qty_multiple_over_max == "restrict":
            return False
        return self.company_id.stock_orderpoint_allow_multiple_over_max

    def _get_qty_to_order(self, force_visibility_days=False, qty_in_progress_by_orderpoint=None):
        self.ensure_one()
        visibility_days = self.visibility_days
        if force_visibility_days is not False:
            visibility_days = force_visibility_days
        qty_to_order = 0.0
        qty_in_progress_by_orderpoint = qty_in_progress_by_orderpoint or {}
        qty_in_progress = qty_in_progress_by_orderpoint.get(self.id)
        if qty_in_progress is None:
            qty_in_progress = self._quantity_in_progress()[self.id]
        rounding = self.product_uom.rounding
        if float_compare(self.qty_forecast, self.product_min_qty, precision_rounding=rounding) < 0:
            product_context = self._get_product_context(visibility_days=visibility_days)
            qty_forecast_with_visibility = (
                self.product_id.with_context(**product_context).read(["virtual_available"])[0]["virtual_available"]
                + qty_in_progress
            )
            qty_to_order = max(self.product_min_qty, self.product_max_qty) - qty_forecast_with_visibility
            remainder = (self.qty_multiple > 0.0 and qty_to_order % self.qty_multiple) or 0.0
            if (
                float_compare(remainder, 0.0, precision_rounding=rounding) > 0
                and float_compare(self.qty_multiple - remainder, 0.0, precision_rounding=rounding) > 0
            ):
                if (
                    float_is_zero(self.product_max_qty, precision_rounding=rounding)
                    or self._is_qty_multiple_over_max_allowed()
                ):
                    qty_to_order += self.qty_multiple - remainder
                else:
                    qty_to_order -= remainder
        return qty_to_order

    def update_qty_to_order(self):
        # Redefinimos ya que el metodo _compute_qty_to_order es privado
        valid_orderpoints = self.exists()
        if valid_orderpoints:
            valid_orderpoints._compute_qty_to_order()

    def _cron_compute_rotation(self):
        """Cron method to compute the rotation of orderpoints."""
        orderpoints = self.with_context(active_test=False).search([])
        orderpoints._compute_rotation()
        return True
