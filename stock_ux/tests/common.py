##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
"""Configuración de escenario de las suites de stock_ux.

Las tres categorías de datos, separadas a propósito:

- **Entorno** (de la base): la compañía y su almacén. Recrearlos es caro y no
  aporta señal.
- **Configuración del escenario** (la crea el test): los tipos de operación con
  sus banderas, que es lo que decide qué se está probando. Se crean propios
  para no depender de cómo esté configurada la base.
- **Documentos** (siempre los crea el test): pickings, moves y quants.

Ningún assert se apoya en registros que el test no haya creado.
"""

from odoo.tests import TransactionCase, tagged

from .invariants import StockUxInvariants


@tagged("post_install", "-at_install")
class StockUxCommon(TransactionCase, StockUxInvariants):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.company.id)], limit=1)
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.customer_location = cls.env.ref("stock.stock_location_customers")
        cls.supplier_location = cls.env.ref("stock.stock_location_suppliers")

        cls.partner = cls.env["res.partner"].create({"name": "Cliente UX de prueba"})
        cls.product = cls.env["product.product"].create(
            {"name": "Producto UX almacenable", "is_storable": True, "list_price": 100.0}
        )
        cls.product_b = cls.env["product.product"].create(
            {"name": "Producto UX almacenable B", "is_storable": True, "list_price": 50.0}
        )

        # Tipos de operación propios: las banderas son lo que decide qué se prueba,
        # así que no se heredan de la configuración de la base.
        cls.out_type = cls._crear_picking_type(cls.warehouse.out_type_id, "UX Salida")
        cls.in_type = cls._crear_picking_type(cls.warehouse.in_type_id, "UX Recepción")
        cls.int_type = cls._crear_picking_type(cls.warehouse.int_type_id, "UX Interna")

    @classmethod
    def _crear_picking_type(cls, plantilla, nombre):
        """Copia un tipo del almacén y apaga todas las banderas de stock_ux.

        Cada test enciende explícitamente la que va a probar: así el escenario
        dice qué se está probando, en vez de heredarlo de la base.
        """
        return plantilla.copy(
            {
                "name": nombre,
                "sequence_code": nombre.replace(" ", "")[:5].upper(),
                "block_additional_quantity": False,
                "block_picking_deletion": False,
                "block_manual_lines": False,
                "restrict_number_package": False,
                "number_of_packages": False,
            }
        )

    @classmethod
    def _poner_stock(cls, product, cantidad, location=None):
        """Deja stock disponible del producto en la ubicación indicada."""
        cls.env["stock.quant"]._update_available_quantity(product, location or cls.stock_location, cantidad)

    def _crear_picking(self, picking_type=None, lineas=None, location=None, location_dest=None):
        """Crea un picking con sus moves. `lineas` es una lista de (producto, cantidad)."""
        picking_type = picking_type or self.out_type
        lineas = lineas if lineas is not None else [(self.product, 10.0)]
        origen = location or picking_type.default_location_src_id or self.stock_location
        destino = location_dest or picking_type.default_location_dest_id or self.customer_location
        return self.env["stock.picking"].create(
            {
                "partner_id": self.partner.id,
                "picking_type_id": picking_type.id,
                "location_id": origen.id,
                "location_dest_id": destino.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": producto.id,
                            "product_uom_qty": cantidad,
                            "product_uom": producto.uom_id.id,
                            "location_id": origen.id,
                            "location_dest_id": destino.id,
                        },
                    )
                    for producto, cantidad in lineas
                ],
            }
        )

    def _crear_usuario(self, nombre, grupos):
        """Usuario interno con los grupos indicados (lista de xml ids)."""
        return (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": nombre,
                    "login": "%s@ux.test" % nombre.lower().replace(" ", "."),
                    "email": "%s@ux.test" % nombre.lower().replace(" ", "."),
                    "company_id": self.company.id,
                    "company_ids": [(6, 0, self.company.ids)],
                    "group_ids": [(6, 0, [self.env.ref(g).id for g in grupos])],
                }
            )
        )
