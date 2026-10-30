##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class StockPickingStateDetail(models.Model):
    _name = "stock.picking.state_detail"
    _description = "Transfer State Detail"
    _order = "sequence, id"

    name = fields.Char(
        copy=False,
        required=True,
    )
    sequence = fields.Integer(copy=False, default=10)
    active = fields.Boolean(default=True)
    picking_type = fields.Selection(
        string="Operation Type",
        required=True,
        selection=[
            ("internal", "Internal Transfer"),
            ("outgoing", "Delivery"),
            ("incoming", "Receipt"),
            ("dropship", "Dropship"),
        ],
    )
    state = fields.Selection(
        string="Status",
        required=True,
        selection=[
            ("draft", "Draft"),
            ("cancel", "Cancelled"),
            ("waiting", "Waiting Another Operation"),
            ("confirmed", "Waiting"),
            ("assigned", "Ready"),
            ("done", "Done"),
        ],
    )
    picking_ids = fields.One2many(
        "stock.picking",
        "state_detail_id",
        "Pickings",
    )
