##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestDeclaredValue(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.warehouse.out_type_id.automatic_declare_value = True
        partner_vals = {"name": "Declared Value Customer"}
        if "partner_state" in cls.env["res.partner"]._fields:
            # sale_exception_partner_state manda a excepción los pedidos de un
            # contacto sin aprobar, y sin confirmar no hay entrega que medir
            partner_vals["partner_state"] = "approved"
        cls.partner = cls.env["res.partner"].create(partner_vals)
        cls.pricelist = cls.env["product.pricelist"].create(
            {
                "name": "Declared Value Pricelist",
                "currency_id": cls.env.company.currency_id.id,
            }
        )
        cls.product_a = cls._create_product("DV-A", 100.0)
        cls.product_b = cls._create_product("DV-B", 250.0)

    @classmethod
    def _create_product(cls, code, price):
        return cls.env["product.product"].create(
            {
                "name": code,
                "default_code": code,
                "type": "consu",
                "is_storable": True,
                "list_price": price,
            }
        )

    def _set_stock(self, product, qty):
        self.env["stock.quant"]._update_available_quantity(product, self.warehouse.lot_stock_id, qty)

    def _create_order(self, lines):
        """Confirma y vacía el entorno: en la UI confirmar el pedido es su propio request."""
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "pricelist_id": self.pricelist.id,
                "order_line": [(0, 0, {"product_id": product.id, "product_uom_qty": qty}) for product, qty in lines],
            }
        )
        order.action_confirm()
        self.env.flush_all()
        return order

    def _line_price(self, order, product):
        return order.order_line.filtered(lambda x: x.product_id == product).price_reduce_taxexcl

    def test_partial_delivery_with_stock_for_backorder(self):
        """El movimiento del backorder queda reservado al validar y no se declara."""
        self._set_stock(self.product_a, 1000)
        order = self._create_order([(self.product_a, 100)])
        picking = order.picking_ids
        picking.action_assign()
        picking.move_ids.quantity = 30
        picking.move_ids.picked = True

        picking.with_context(skip_backorder=True).button_validate()

        price = self._line_price(order, self.product_a)
        backorder = order.picking_ids - picking
        self.assertAlmostEqual(picking.declared_value, price * 30, places=2)
        self.assertAlmostEqual(backorder.declared_value, price * 70, places=2)

    def test_partial_delivery_without_stock_for_backorder(self):
        self._set_stock(self.product_a, 30)
        order = self._create_order([(self.product_a, 100)])
        picking = order.picking_ids
        picking.action_assign()
        picking.move_ids.picked = True

        picking.with_context(skip_backorder=True).button_validate()

        price = self._line_price(order, self.product_a)
        self.assertAlmostEqual(picking.declared_value, price * 30, places=2)

    def test_full_delivery(self):
        self._set_stock(self.product_a, 1000)
        order = self._create_order([(self.product_a, 100)])
        picking = order.picking_ids
        picking.action_assign()
        picking.move_ids.picked = True

        picking.with_context(skip_backorder=True).button_validate()

        price = self._line_price(order, self.product_a)
        self.assertAlmostEqual(picking.declared_value, price * 100, places=2)

    def test_move_entirely_backordered(self):
        """Un movimiento que no salió se muda entero al backorder y no se declara."""
        self._set_stock(self.product_a, 1000)
        order = self._create_order([(self.product_a, 100), (self.product_b, 10)])
        picking = order.picking_ids
        picking.action_assign()

        picking.with_context(skip_backorder=True).button_validate()

        price_a = self._line_price(order, self.product_a)
        self.assertAlmostEqual(picking.declared_value, price_a * 100, places=2)

    def test_kit_partial_delivery(self):
        """En kits el prorrateo promedia por componente: sólo deben entrar los hechos."""
        if "mrp.bom" not in self.env:
            self.skipTest("mrp no instalado")
        component_a = self._create_product("DV-C1", 10.0)
        component_b = self._create_product("DV-C2", 20.0)
        kit = self._create_product("DV-KIT", 1000.0)
        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": kit.product_tmpl_id.id,
                "product_qty": 1.0,
                "type": "phantom",
                "bom_line_ids": [
                    (0, 0, {"product_id": component_a.id, "product_qty": 2.0}),
                    (0, 0, {"product_id": component_b.id, "product_qty": 3.0}),
                ],
            }
        )
        self._set_stock(component_a, 1000)
        self._set_stock(component_b, 1000)
        order = self._create_order([(kit, 10)])
        picking = order.picking_ids
        picking.action_assign()
        for move in picking.move_ids:
            move.quantity = 12 if move.product_id == component_a else 18
        picking.move_ids.picked = True

        picking.with_context(skip_backorder=True).button_validate()

        price = self._line_price(order, kit)
        self.assertAlmostEqual(picking.declared_value, price * 6, places=2)
