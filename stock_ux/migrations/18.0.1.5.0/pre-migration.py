# Copyright 2025 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    """Create index on warehouse_id for stock_warehouse_orderpoint table.

    Backport from v19: This index improves query performance when filtering
    orderpoints by warehouse, which is a common operation.
    """
    # Check if index already exists
    cr.execute("""
        ALTER TABLE stock_warehouse_orderpoint
        ADD COLUMN qty_to_order_computed numeric
    """)
