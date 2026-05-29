# Copyright 2026 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Create stock_orderpoint_allow_multiple_over_max and qty_multiple_over_max
    columns to support multiple-over-max feature in stock orderpoints.
    """
    _logger.info("Starting migration: creating multiple-over-max columns")

    cr.execute("""
        ALTER TABLE res_company
        ADD COLUMN IF NOT EXISTS stock_orderpoint_allow_multiple_over_max boolean
    """)
    cr.execute("""
        UPDATE res_company
           SET stock_orderpoint_allow_multiple_over_max = TRUE
         WHERE stock_orderpoint_allow_multiple_over_max IS NULL
    """)

    cr.execute("""
        ALTER TABLE stock_warehouse_orderpoint
        ADD COLUMN IF NOT EXISTS qty_multiple_over_max varchar
    """)
    cr.execute("""
        UPDATE stock_warehouse_orderpoint
           SET qty_multiple_over_max = 'company'
         WHERE qty_multiple_over_max IS NULL
    """)
