##############################################################################
#
#    Copyright (C) 2026  ADHOC SA  (http://www.adhoc.com.ar)
#    All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import api, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.depends("picking_type_id.is_repairable")
    def _compute_is_repairable(self):
        # The operation type is the only switch: core also requires `return_id`, which
        # only the "Return" wizard sets, so migrated returns and transfers created by
        # hand never offer the repair button.
        for picking in self:
            picking.is_repairable = picking.picking_type_id.is_repairable
