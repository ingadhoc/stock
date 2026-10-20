# Copyright 2026 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import SUPERUSER_ID, api
from odoo.tools import split_every

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Recompute qty_to_order_computed of orderpoints with a multiple.

    18.0.1.11.0 added the multiple-over-max setting without recomputing the stored
    value, so orderpoints without moves since then keep the previous rounding.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    orderpoints = env["stock.warehouse.orderpoint"].with_context(active_test=False).search([("qty_multiple", ">", 0)])
    field = orderpoints._fields["qty_to_order_computed"]
    _logger.info("Recomputing qty_to_order_computed for %d orderpoints with a multiple", len(orderpoints))
    for batch in split_every(500, orderpoints.ids, orderpoints.browse):
        env.add_to_compute(field, batch)
        batch.flush_recordset(["qty_to_order_computed"])
        env.invalidate_all()
