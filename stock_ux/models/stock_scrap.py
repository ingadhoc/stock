##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import api, models


class StockScrap(models.Model):
    _inherit = "stock.scrap"

    @api.depends("company_id", "picking_id", "move_ids.move_line_ids.location_id")
    def _compute_location_id(self):
        """La ubicación de origen sigue al movimiento, que es el único lugar donde se la
        puede corregir una vez hecho el desecho."""
        from_move = self.filtered(lambda x: x.move_ids.move_line_ids.location_id)
        super(StockScrap, self - from_move)._compute_location_id()
        for scrap in from_move:
            scrap.location_id = scrap.move_ids.move_line_ids.location_id[0]
