##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class Location(models.Model):
    _inherit = "stock.location"

    @api.onchange("replenish_location")
    def _onchange_replenish_location(self):
        if self.replenish_location == False:
            warning = {
                "title": ("Warning!"),
                "message": (
                    "By deactivating this function,"
                    " temporary replenishment rules will not be generated to suggest products to replenish according to the forecasts"
                ),
            }
            return {"warning": warning}
