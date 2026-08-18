from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("stock_ux_multiwarehouse")
class TestMultiwarehouseGroupBranch(TransactionCase):
    """El permiso "Gestionar varios almacenes" debe seguir a los almacenes del
    árbol de compañías: se activa cuando una compañía tiene sucursales con
    almacenes (aunque cada una tenga uno solo) y se desactiva cuando esos
    almacenes o sus compañías dejan de estar activos. En modo test crear una
    ``res.company`` le crea su almacén (ver ``stock/models/res_company.py``).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Warehouse = cls.env["stock.warehouse"]
        cls.group_user = cls.env.ref("base.group_user")
        cls.group_multi_wh = cls.env.ref("stock.group_stock_multi_warehouses")
        cls.parent_company = cls.env["res.company"].create({"name": "UX Madre"})

    def _create_branch(self, name="UX Sucursal"):
        return self.env["res.company"].create({"name": name, "parent_id": self.parent_company.id})

    def _warehouses_of(self, company):
        return self.Warehouse.with_context(active_test=False).search([("company_id", "=", company.id)])

    def _native_max_count(self):
        """Conteo del método nativo: máximo de almacenes activos de UNA compañía."""
        groups = self.Warehouse.sudo()._read_group([("active", "=", True)], ["company_id"], aggregates=["__count"])
        return max((count for _company, count in groups), default=0)

    def test_warehouses_are_counted_by_company_tree(self):
        branch = self._create_branch()
        self.assertEqual(branch.root_id, self.parent_company)

        native = self.Warehouse.sudo()._read_group(
            [("active", "=", True), ("company_id", "in", (self.parent_company + branch).ids)],
            ["company_id"],
            aggregates=["__count"],
        )
        self.assertEqual(
            sorted(count for _company, count in native),
            [1, 1],
            "Cada compañía del árbol tiene un solo almacén, por eso el conteo nativo no alcanza.",
        )
        self.assertEqual(
            self.Warehouse._multiwarehouse_count_by_root_company()[self.parent_company],
            2,
            "Madre y sucursal deben contarse juntas bajo la compañía raíz.",
        )

    def test_branch_warehouse_activates_multi_wh_group(self):
        # Partir del permiso desactivado: si ya viene implicado el test no
        # probaría nada.
        self.group_user.write({"implied_ids": [(3, self.group_multi_wh.id)]})
        self.assertNotIn(self.group_multi_wh, self.group_user.implied_ids)
        self.assertEqual(
            self._native_max_count(),
            1,
            "Ninguna compañía sola llega a dos almacenes; si no, el nativo activaría el "
            "permiso por su cuenta y el test dejaría de discriminar.",
        )

        # Crear la sucursal crea su almacén y con eso corre _check_multiwarehouse_group.
        self._create_branch()

        self.assertIn(
            self.group_multi_wh,
            self.group_user.implied_ids,
            "Con una madre y una sucursal, cada una con su almacén, el permiso "
            "'Gestionar varios almacenes' debe activarse automáticamente.",
        )

    def test_archived_branch_deactivates_group(self):
        branch = self._create_branch()
        self.assertIn(self.group_multi_wh, self.group_user.implied_ids)

        # Archivar la compañía no archiva su almacén: el conteo tiene que
        # ignorarlo igual y revisar el permiso.
        branch.write({"active": False})

        self.assertTrue(all(self._warehouses_of(branch).mapped("active")))
        self.assertEqual(self.Warehouse._multiwarehouse_count_by_root_company()[self.parent_company], 1)
        self.assertNotIn(
            self.group_multi_wh,
            self.group_user.implied_ids,
            "Archivada la sucursal queda un solo almacén en juego: el permiso debe desactivarse.",
        )

    def test_unarchived_branch_activates_group_again(self):
        branch = self._create_branch()
        branch.write({"active": False})
        self.assertNotIn(self.group_multi_wh, self.group_user.implied_ids)

        branch.write({"active": True})

        self.assertIn(self.group_multi_wh, self.group_user.implied_ids)

    def test_archived_branch_warehouse_deactivates_group(self):
        branch = self._create_branch()
        self.assertIn(self.group_multi_wh, self.group_user.implied_ids)

        self._warehouses_of(branch).write({"active": False})

        self.assertNotIn(self.group_multi_wh, self.group_user.implied_ids)

    def test_single_warehouse_per_company_deactivates_group(self):
        """Sin sucursales, con un solo almacén por compañía, el permiso se
        desactiva igual que en el nativo (sin regresión para el caso simple)."""
        self.group_user.write({"implied_ids": [(4, self.group_multi_wh.id)]})
        self.assertEqual(self._native_max_count(), 1)

        self.Warehouse._check_multiwarehouse_group()

        self.assertNotIn(self.group_multi_wh, self.group_user.implied_ids)
