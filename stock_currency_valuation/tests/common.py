from odoo import fields


def set_on_hand(env, product, quantity):
    warehouse = env["stock.warehouse"].search([("company_id", "=", env.company.id)], limit=1)
    env["stock.quant"].with_context(inventory_mode=True).create(
        {"product_id": product.id, "location_id": warehouse.lot_stock_id.id, "inventory_quantity": quantity}
    ).action_apply_inventory()


def receive_purchase(env, product, quantity, price_unit, currency, currency_rate=0.0, discount=0.0):
    """Compra sin impuestos y su recepcion, opcionalmente con cotizacion manual en el picking."""
    order = env["purchase.order"].create(
        {
            "partner_id": env["res.partner"].create({"name": "Proveedor"}).id,
            "currency_id": currency.id,
            "order_line": [
                (
                    0,
                    0,
                    {
                        "product_id": product.id,
                        "product_qty": quantity,
                        "price_unit": price_unit,
                        "discount": discount,
                        "taxes_id": [(5,)],
                    },
                )
            ],
        }
    )
    order.button_confirm()
    order.picking_ids.currency_rate = currency_rate
    order.picking_ids.button_validate()
    return order


def bill_with_price_difference(env, product):
    """OC en USD sin IVA 10 x 52,02, salen 4, factura 10 x 46 con IVA 21%."""
    tax = env["account.tax"].create(
        {"name": "IVA 21% compras", "amount": 21.0, "type_tax_use": "purchase", "company_id": env.company.id}
    )
    order = receive_purchase(env, product, 10.0, 52.02, env.ref("base.USD"))
    set_on_hand(env, product, 6.0)
    order.action_create_invoice()
    bill = order.invoice_ids
    bill.invoice_date = fields.Date.today()
    bill.invoice_line_ids.write({"price_unit": 46.0, "tax_ids": [(6, 0, tax.ids)]})
    bill.action_post()
    return bill


def has_purchase_journal(env):
    return bool(env["account.journal"].search([("type", "=", "purchase"), ("company_id", "=", env.company.id)]))
