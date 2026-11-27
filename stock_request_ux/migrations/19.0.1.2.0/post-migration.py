import logging

from odoo import SUPERUSER_ID, api
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


def _kit_qty_per_unit(request, bom_line):
    """Quantity of the component of ``bom_line`` for one unit of the kit of ``request``."""
    bom = bom_line.bom_id
    kit_qty = request.product_id.uom_id._compute_quantity(1.0, bom.product_uom_id, round=False) / bom.product_qty
    for line, line_data in bom.explode(request.product_id, kit_qty)[1]:
        if line == bom_line:
            return line.product_uom_id._compute_quantity(line_data["qty"], line.product_id.uom_id, round=False)
    return 0.0


def restore_kit_allocations(env):
    """Give back to the component moves of a kit the quantity they ask for.

    The migration of stock_request 19.0.1.1.0 limited the open allocations to what the request
    still needs, but compared the kits of the request with the units of the component, so the
    allocation of a move of 192 cans for 8 packs was left at 8. Each allocation asks again for what
    the request needs of that component, never more than what its move moves.
    """
    if "bom_line_id" not in env["stock.move"]._fields:
        return env["stock.request"]
    allocations = env["stock.request.allocation"].search(
        [
            ("stock_move_id.state", "not in", ["done", "cancel"]),
            ("stock_move_id.bom_line_id", "!=", False),
        ]
    )
    requests = env["stock.request"]
    for alloc in allocations:
        move = alloc.stock_move_id
        request = alloc.stock_request_id
        if move.product_id == request.product_id or len(move.allocation_ids) > 1:
            continue
        product_uom = move.product_id.uom_id
        qty_per_unit = _kit_qty_per_unit(request, move.bom_line_id)
        if product_uom.is_zero(qty_per_unit):
            continue
        received = sum(
            other.allocated_product_qty
            for other in request.allocation_ids - alloc
            if other.stock_move_id.bom_line_id == move.bom_line_id and other.stock_move_id.state == "done"
        )
        wanted = min(move.product_qty, max(request.product_qty * qty_per_unit - received, 0.0))
        if float_compare(alloc.requested_product_qty, wanted, precision_rounding=product_uom.rounding) >= 0:
            continue
        alloc.requested_product_uom_qty = product_uom._compute_quantity(wanted, alloc.product_uom_id, round=False)
        requests |= request
    _logger.info("Restored the quantity of the kit allocations of %s stock requests", len(requests))
    return requests


def link_backorder_moves(env):
    """Give the moves of a backorder the allocation of the move they come from.

    Up to now stock_request_ux did not let the split copy the allocations, so the move that waits
    for the rest of a partial receipt was not part of its request. It takes what was still open on
    the allocation of its source move, which keeps only what it received. A move already received
    takes all that was open and keeps as allocated what it moved, so its own backorder takes the
    rest in the next pass: a chain of backorders is linked one link per pass. A move is left alone
    when its source move belongs to more than one request, or when the order asks for the same
    product twice: there it is not clear which line it belongs to.
    """
    domain = [
        ("picking_id.backorder_id", "!=", False),
        ("allocation_ids", "=", False),
        ("state", "!=", "cancel"),
        ("origin_returned_move_id", "=", False),
        ("picking_id.backorder_id.move_ids.allocation_ids", "!=", False),
    ]
    requests = env["stock.request"]
    seen = env["stock.move"]
    left = env["stock.move"]
    while True:
        moves = env["stock.move"].search(domain + [("id", "not in", seen.ids)], order="id")
        if not moves:
            break
        seen |= moves
        for move in moves:
            sources = move.picking_id.backorder_id.move_ids.filtered(
                lambda m, mv=move: m.product_id == mv.product_id
                and m.allocation_ids
                and m.state == "done"
                and ("bom_line_id" not in m._fields or m.bom_line_id == mv.bom_line_id)
            )
            source_allocs = sources.allocation_ids
            request = source_allocs.stock_request_id
            if len(sources) != 1 or len(request) != 1:
                left |= move
                continue
            if request.order_id and env["stock.request"].search_count(
                [
                    ("order_id", "=", request.order_id.id),
                    ("product_id", "=", request.product_id.id),
                    ("id", "!=", request.id),
                ]
            ):
                left |= move
                continue
            product_uom = move.product_id.uom_id
            open_qty = source_allocs.requested_product_qty - source_allocs.allocated_product_qty
            done = move.state == "done"
            qty = open_qty if done else min(move.product_qty, open_qty)
            if float_compare(qty, 0.0, precision_rounding=product_uom.rounding) <= 0:
                left |= move
                continue
            env["stock.request.allocation"].create(
                {
                    "stock_request_id": request.id,
                    "stock_move_id": move.id,
                    "requested_product_uom_qty": product_uom._compute_quantity(
                        qty, request.product_uom_id, round=False
                    ),
                    "allocated_product_qty": min(qty, move.product_qty) if done else 0.0,
                }
            )
            source_allocs.requested_product_uom_qty = product_uom._compute_quantity(
                source_allocs.requested_product_qty - qty, source_allocs.product_uom_id, round=False
            )
            requests |= request
        env.flush_all()
    _logger.info(
        "Linked the backorder moves of %s stock requests; %s moves were left without allocation",
        len(requests),
        len(left),
    )
    return requests


def settle_states(env, requests):
    """A request closed because of a missing allocation follows its quantities again.

    Without stock_request_mrp a request of a kit counts the units of its components, so its state
    is left to the install of that module, which settles the requests of kits.
    """
    if not env["ir.module.module"].search_count([("name", "=", "stock_request_mrp"), ("state", "=", "installed")]):
        requests = requests.filtered(
            lambda r: not r.product_id.product_tmpl_id.bom_ids.filtered(lambda b: b.type == "phantom")
        )
    precision = requests.env["decimal.precision"].precision_get("Product Unit")
    closed = requests.filtered(lambda r: r.state in ("done", "cancel"))
    reopened = closed.filtered(lambda r: float_compare(r.qty_in_progress, 0, precision_digits=precision) > 0)
    reopened.write({"state": "open"})
    requests.filtered(lambda r: r.state == "open").check_done()
    _logger.info("Reopened %s stock requests", len(reopened.filtered(lambda r: r.state == "open")))


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    requests = restore_kit_allocations(env)
    env.flush_all()
    requests |= link_backorder_moves(env)
    env.flush_all()
    settle_states(env, requests)
