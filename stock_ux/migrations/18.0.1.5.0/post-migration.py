# Copyright 2025 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Populate qty_to_order_computed for existing orderpoints.

    Backport from v19: qty_to_order_computed is now a stored field.
    This migration computes the initial values for all existing orderpoints.
    Processing is done in batches to avoid memory issues on large databases.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    _logger.info("Starting migration: populating qty_to_order_computed for orderpoints")

    # Get all orderpoints (including archived ones)
    orderpoints = env["stock.warehouse.orderpoint"].with_context(active_test=False).search([])
    total = len(orderpoints)

    if not total:
        _logger.info("No orderpoints found, skipping migration")
        return

    _logger.info("Found %d orderpoints to process", total)

    # Process in batches to avoid memory issues
    batch_size = 500
    processed = 0

    for i in range(0, total, batch_size):
        batch = orderpoints[i : i + batch_size]
        try:
            batch._compute_qty_to_order_computed()
            processed += len(batch)
            _logger.info("Processed %d/%d orderpoints", processed, total)
            # pylint: disable=invalid-commit
            # Commit is required in migration scripts to avoid memory issues on large databases
            cr.commit()
        except Exception as e:
            _logger.error("Error processing batch %d-%d: %s", i, i + batch_size, e)
            cr.rollback()
            # Try to process individually on error
            for orderpoint in batch:
                try:
                    orderpoint._compute_qty_to_order_computed()
                    processed += 1
                    # pylint: disable=invalid-commit
                    cr.commit()
                except Exception as e2:
                    _logger.error("Error processing orderpoint %d: %s", orderpoint.id, e2)
                    cr.rollback()

    _logger.info("Migration completed: %d/%d orderpoints processed successfully", processed, total)
