from odoo import fields, models, tools
from odoo.tools import float_is_zero


class StockAverageCostReport(models.AbstractModel):
    _inherit = "stock.avco.report"

    valuation_currency_id = fields.Many2one(
        "res.currency",
        related="product_id.valuation_currency_id",
        string="Valuation Currency",
    )
    value_in_currency = fields.Monetary(
        string="Value in Currency",
        currency_field="valuation_currency_id",
        required=True,
    )
    added_value_in_currency = fields.Monetary(
        string="Added Value in Currency",
        compute="_compute_cumulative_fields",
        currency_field="valuation_currency_id",
    )
    total_value_in_currency = fields.Monetary(
        string="Total Value in Currency",
        compute="_compute_cumulative_fields",
        currency_field="valuation_currency_id",
    )
    avco_value_in_currency = fields.Monetary(
        string="AVCO Value in Currency",
        compute="_compute_cumulative_fields",
        currency_field="valuation_currency_id",
    )

    def init(self):
        """MAINTENANCE NOTE: this view is a COPY of the standard one in
        ``stock_account/report/stock_avco_audit_report.py::init`` with the
        ``value_in_currency`` column added to both legs of the UNION. It does not call
        ``super()`` —a view cannot be extended column by column— so it has to be
        RE-SYNCED whenever Odoo touches theirs. Drift here is silent: the view builds
        fine and the numbers come out wrong. ``test_avco_report_quantity_in_product_uom``
        covers the last one that happened (the UoM conversion was missing)."""
        tools.drop_view_if_exists(self.env.cr, "stock_avco_report")
        query = """
CREATE OR REPLACE VIEW stock_avco_report AS (
SELECT
    sm.id AS id,
    sm.product_id,
    sm.date,
    picking.user_id,
    sm.company_id,
    sm.reference,
    CASE WHEN sm.is_in THEN sm.value ELSE -sm.value END AS value,
    CASE WHEN sm.is_in THEN sm.value_in_currency ELSE -sm.value_in_currency END AS value_in_currency,
    CASE WHEN sm.is_in THEN sm.quantity * (um.factor / up.factor) ELSE -sm.quantity * (um.factor / up.factor) END AS quantity,
    'stock.move' AS res_model_name,
    'Operation' AS description
FROM
    stock_move sm
LEFT JOIN
    stock_picking picking ON sm.picking_id = picking.id
LEFT JOIN
    product_product pp ON sm.product_id = pp.id
LEFT JOIN
    product_template pt ON pp.product_tmpl_id = pt.id
LEFT JOIN
    product_category pc ON pt.categ_id = pc.id
LEFT JOIN
    res_company company ON sm.company_id = company.id
LEFT JOIN
    uom_uom um ON um.id = sm.product_uom
LEFT JOIN
    uom_uom up ON up.id = pt.uom_id
WHERE
    sm.state = 'done'
    AND (sm.is_in = TRUE OR sm.is_out = TRUE)
    -- Ignore moves for standard cost method. Only display the list of cost updates
    AND (
        (pt.categ_id IS NOT NULL AND pc.property_cost_method ->> company.id::text IN ('fifo', 'average'))
        OR (pt.categ_id IS NULL OR (pc.property_cost_method IS NULL OR pc.property_cost_method ->> company.id::text IS NULL) AND company.cost_method IN ('fifo', 'average'))
    )
UNION ALL
SELECT
    -pv.id,
    pv.product_id,
    pv.date,
    pv.user_id,
    pv.company_id,
    'Adjustment' AS reference, -- Set a fixed string for the reference
    pv.value,
    pv.value_in_currency,
    0 AS quantity, -- Set quantity to 0 as requested,
    'product.value' AS res_model_name,
    pv.description
FROM
    product_value pv
WHERE
    pv.move_id IS NULL
);
"""
        self.env.cr.execute(query)

    def _compute_cumulative_fields(self):
        """MAINTENANCE NOTE: copy of the standard computation, carrying the
        secondary-currency amounts alongside the company-currency ones. Same deal as
        ``init`` above: no ``super()``, so it has to be re-synced on upgrades.
        """
        total_records_grouped = (
            self.env["stock.avco.report"]
            .search(
                [("product_id", "in", self.product_id.mapped("id")), ("company_id", "in", self.company_id.mapped("id"))]
            )
            .grouped(lambda record: (record.product_id, record.company_id))
        )
        precision = self.env["decimal.precision"].precision_get("Product Unit")

        for records in self.grouped(lambda record: (record.product_id, record.company_id)).values():
            current_page_records = records.sorted("date, id")
            total_records = total_records_grouped.get((records.product_id, records.company_id)).sorted("date, id")
            added_value = 0.0
            total_value = 0.0
            total_quantity = 0.0
            avco = 0.0
            added_value_in_currency = 0.0
            total_value_in_currency = 0.0
            avco_in_currency = 0.0
            for record in total_records:
                qty = record.quantity
                if record.res_model_name == "stock.move":
                    previous_qty = total_quantity
                    total_quantity += qty
                    if qty > 0:
                        added_value = record.value
                        added_value_in_currency = record.value_in_currency
                        if previous_qty > 0:
                            total_value += added_value
                            total_value_in_currency += added_value_in_currency
                            avco = (
                                total_value / total_quantity
                                if not float_is_zero(total_quantity, precision_digits=precision)
                                else avco
                            )
                            avco_in_currency = (
                                total_value_in_currency / total_quantity
                                if not float_is_zero(total_quantity, precision_digits=precision)
                                else avco_in_currency
                            )
                        else:
                            avco = added_value / qty if qty else avco
                            total_value = avco * total_quantity
                            avco_in_currency = added_value_in_currency / qty if qty else avco_in_currency
                            total_value_in_currency = avco_in_currency * total_quantity
                    else:
                        added_value = avco * qty
                        total_value += added_value
                        added_value_in_currency = avco_in_currency * qty
                        total_value_in_currency += added_value_in_currency

                elif record.res_model_name == "product.value":
                    avco = record.value
                    added_value = (avco * total_quantity) - total_value
                    total_value = avco * total_quantity
                    avco_in_currency = record.value_in_currency
                    added_value_in_currency = (avco_in_currency * total_quantity) - total_value_in_currency
                    total_value_in_currency = avco_in_currency * total_quantity

                if record in current_page_records:
                    record.added_value = added_value
                    record.total_value = total_value
                    record.total_quantity = total_quantity
                    record.avco_value = avco
                    record.added_value_in_currency = added_value_in_currency
                    record.total_value_in_currency = total_value_in_currency
                    record.avco_value_in_currency = avco_in_currency
