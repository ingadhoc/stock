##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from collections import defaultdict

from odoo import models


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    def _multiwarehouse_count_by_root_company(self):
        """Almacenes activos de compañías activas, contados por árbol de
        compañías (la raíz suma los de sus sucursales). Para una compañía sin
        sucursales ``root_id`` es ella misma."""
        count_by_root = defaultdict(int)
        groups = (
            self.env["stock.warehouse"]
            .sudo()
            ._read_group(
                [("active", "=", True), ("company_id.active", "=", True)], ["company_id"], aggregates=["__count"]
            )
        )
        for company, count in groups:
            count_by_root[company.root_id] += count
        return count_by_root

    def _check_multiwarehouse_group(self):
        """Activa o desactiva "Gestionar varios almacenes" contando los
        almacenes por árbol de compañías.

        El nativo los agrupa por ``company_id``, así que un almacén por sucursal
        deja el conteo en 1 por compañía y el permiso nunca se activa. Además
        cuenta los almacenes de compañías archivadas, con lo cual archivar una
        sucursal no baja el conteo.

        Mantener la lógica de activación / desactivación sincronizada con
        ``stock.warehouse._check_multiwarehouse_group`` en cada upgrade.
        """
        max_count = max(self._multiwarehouse_count_by_root_company().values(), default=0)
        group_user = self.env.ref("base.group_user")
        group_multi_warehouses = self.env.ref("stock.group_stock_multi_warehouses")
        if max_count <= 1:
            if group_multi_warehouses in group_user.implied_ids:
                group_user.write({"implied_ids": [(3, group_multi_warehouses.id)]})
                group_multi_warehouses.write({"user_ids": [(3, user.id) for user in group_user.all_user_ids]})
            return
        if group_multi_warehouses in group_user.implied_ids:
            return
        group_multi_locations = self.env.ref("stock.group_stock_multi_locations")
        if group_multi_locations not in group_user.implied_ids:
            self.env["res.config.settings"].create({"group_stock_multi_locations": True}).execute()
        group_user.write({"implied_ids": [(4, group_multi_warehouses.id), (4, group_multi_locations.id)]})
