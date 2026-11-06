##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo.addons.sale_order_type_invoice_policy.tests.common import SaleOrderTypeInvoicePolicyCommon


class SaleOrderTypeInvoicePolicyInvoiceLinkCommon(SaleOrderTypeInvoicePolicyCommon):
    """Escenario e invariantes del puente entre la política por tipo y el link de albaranes."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # entrega en un paso: así order.picking_ids es la salida y nada más
        cls.warehouse.delivery_steps = "ship_only"
        cls.product_order = cls.env["product.product"].create(
            {
                "name": "Invoice Policy Product (order)",
                "type": "consu",
                "is_storable": True,
                "invoice_policy": "order",
                "list_price": 100.0,
            }
        )
        cls.env["stock.quant"]._update_available_quantity(cls.product_order, cls.warehouse.lot_stock_id, 100.0)

    def _facturar(self, order):
        invoice = order._create_invoices(final=True)
        invoice.action_post()
        return invoice

    def _nota_credito(self, invoice):
        refund = invoice._reverse_moves([{"invoice_date": invoice.invoice_date}])
        refund.action_post()
        return refund

    # -- batería de invariantes -------------------------------------------------

    def assert_vinculo_coherente(self, order):
        """Toda línea de factura enganchada es de la misma línea de venta y de un comprobante vivo."""
        for move in order.picking_ids.move_ids:
            for aml in move.invoice_line_ids:
                self.assertIn(
                    move.sale_line_id,
                    aml.sale_line_ids,
                    "el movimiento quedó enganchado a una línea de otra venta",
                )
                self.assertNotEqual(aml.move_id.state, "cancel", "quedó enganchado a un comprobante cancelado")
