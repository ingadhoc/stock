from odoo import _, models
from odoo.exceptions import UserError


class StockScrap(models.Model):
    _inherit = "stock.scrap"

    def action_validate(self):
        total_scraped = sum(
            scrap.scrap_qty
            for scrap in self.env["stock.scrap"].search(
                [
                    ("product_id", "=", self.product_id.id),
                    ("picking_id", "=", self.picking_id.id),
                    ("state", "=", "done"),
                ]
            )
        )
        total_picking = sum(
            move_id.product_uom_qty for move_id in self.picking_id.move_ids if move_id.product_id == self.product_id
        )
        if self.picking_id and (self.scrap_qty + total_scraped) > total_picking:
            raise UserError(
                _("No se puede desechar una cantidad mayor a la cantidad dentro de la transferencia del producto: %s.")
                % self.product_id.display_name
            )

        return super().action_validate()
