# Copyright 2025 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Create qty_to_order_computed column and warehouse_id index.

    Backport from v19: Adds stored qty_to_order_computed column and
    warehouse_id index to improve query performance.
    """
    # Create qty_to_order_computed column if it doesn't exist
    cr.execute("""
        ALTER TABLE stock_warehouse_orderpoint
        ADD COLUMN IF NOT EXISTS qty_to_order_computed numeric
    """)

    # Create index on warehouse_id if it doesn't exist
    cr.execute("""
        CREATE INDEX IF NOT EXISTS stock_warehouse_orderpoint_warehouse_id_index
        ON stock_warehouse_orderpoint (warehouse_id)
    """)
