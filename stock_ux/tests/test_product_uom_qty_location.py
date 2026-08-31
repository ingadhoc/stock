##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from lxml import etree
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProductUomQtyLocation(TransactionCase):
    """Comportamiento de stock.move.line.product_uom_qty_location ("Net Quantity").

    El compute es relativo a la ubicacion que viaja en el contexto ('location'), que el
    facet de busqueda "Net Quantity Location" inyecta como LISTA (texto tipeado -> str,
    seleccion del desplegable -> id int). Verificamos los tres caminos y el signo.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.stock_loc = cls.warehouse.lot_stock_id
        cls.customer_loc = cls.env.ref("stock.stock_location_customers")
        cls.supplier_loc = cls.env.ref("stock.stock_location_suppliers")
        # sub-ubicacion dentro de Stock, para el caso "origen y destino en la misma ubicacion"
        cls.shelf_loc = cls.env["stock.location"].create(
            {"name": "Shelf Test", "location_id": cls.stock_loc.id, "usage": "internal"}
        )
        cls.product = cls.env["product.product"].create({"name": "Net Qty Test Product", "is_storable": True})

    def _make_move_line(self, src, dest, qty=5.0):
        """Crea una stock.move.line concreta (via su move) entre src y dest."""
        move = self.env["stock.move"].create(
            {
                "product_id": self.product.id,
                "product_uom_qty": qty,
                "location_id": src.id,
                "location_dest_id": dest.id,
            }
        )
        return self.env["stock.move.line"].create(
            {
                "move_id": move.id,
                "product_id": self.product.id,
                "quantity": qty,
                "location_id": src.id,
                "location_dest_id": dest.id,
            }
        )

    def test_00_sin_ubicacion_da_cero(self):
        """Sin 'location' en el contexto, el campo es 0 por diseno."""
        ml = self._make_move_line(self.stock_loc, self.customer_loc)
        self.assertEqual(ml.product_uom_qty_location, 0.0)

    def test_01_salida_por_texto_da_negativo(self):
        """Salida de la ubicacion buscada (facet por TEXTO) -> negativo."""
        ml = self._make_move_line(self.stock_loc, self.customer_loc, qty=5.0)
        ml = ml.with_context(location=[self.stock_loc.complete_name])
        self.assertEqual(ml.product_uom_qty_location, -5.0)

    def test_02_entrada_por_texto_da_positivo(self):
        """Entrada a la ubicacion buscada (origen externo) -> positivo."""
        ml = self._make_move_line(self.supplier_loc, self.stock_loc, qty=5.0)
        ml = ml.with_context(location=[self.stock_loc.complete_name])
        self.assertEqual(ml.product_uom_qty_location, 5.0)

    def test_03_origen_y_destino_en_ubicacion_da_cero(self):
        """Movimiento interno dentro del arbol de la ubicacion buscada -> 0."""
        ml = self._make_move_line(self.stock_loc, self.shelf_loc, qty=5.0)
        ml = ml.with_context(location=[self.stock_loc.complete_name])
        self.assertEqual(ml.product_uom_qty_location, 0.0)

    def test_04_seleccion_por_id_no_crashea_y_da_negativo(self):
        """Facet por SELECCION del desplegable: 'location' llega como [id] (int).

        Antes del fix esto explotaba con AttributeError porque stock.location no tiene
        campo 'reference'. Ahora resuelve por complete_name y da el mismo resultado que
        el path de texto.
        """
        ml = self._make_move_line(self.stock_loc, self.customer_loc, qty=5.0)
        ml = ml.with_context(location=[self.stock_loc.id])
        self.assertEqual(ml.product_uom_qty_location, -5.0)

    def test_05_columna_oculta_sin_ubicacion_en_la_vista(self):
        """La vista de lista debe ocultar la columna cuando no hay 'location' (column_invisible)."""
        view = self.env.ref("stock_ux.view_move_line_tree2")
        arch = etree.fromstring(view.arch)
        nodes = arch.xpath("//field[@name='product_uom_qty_location']")
        self.assertTrue(nodes, "La columna product_uom_qty_location no esta en la vista")
        self.assertEqual(
            nodes[0].get("column_invisible"),
            "not context.get('location', False)",
            "La columna deberia ocultarse por contexto de ubicacion (toggle recuperado)",
        )
