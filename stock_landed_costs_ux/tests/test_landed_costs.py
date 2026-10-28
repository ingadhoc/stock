##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import Command
from odoo.addons.stock_landed_costs.tests.common import TestStockLandedCostsCommon
from odoo.tests import Form, tagged


@tagged("post_install", "-at_install")
class TestLandedCostsUx(TestStockLandedCostsCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # 1 company currency = 2 units of the other currency at the bill date
        cls.other_currency = cls.setup_other_currency("EUR", rates=[("2026-01-01", 2.0)])

    def _create_bill(self, move_type="in_invoice", invoice_currency_rate=None):
        bill = self.env["account.move"].create(
            {
                "move_type": move_type,
                "partner_id": self.supplier_id,
                "invoice_date": "2026-01-15",
                "currency_id": self.other_currency.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.landed_cost.id,
                            "price_unit": 100.0,
                            "tax_ids": False,
                            "is_landed_costs_line": True,
                        }
                    )
                ],
            }
        )
        if invoice_currency_rate:
            bill.invoice_currency_rate = invoice_currency_rate
        bill.action_post()
        return bill

    def _create_landed_costs(self, bill):
        action = bill.button_create_landed_costs()
        return self.env[action["res_model"]].browse(action["res_id"])

    def test_bill_currency_rate(self):
        """The price in company currency uses the rate of the bill, not the one of its date"""
        bill = self._create_bill(invoice_currency_rate=4.0)
        cost_line = self._create_landed_costs(bill).cost_lines
        self.assertRecordValues(
            cost_line,
            [
                {
                    "product_id": self.landed_cost.id,
                    "price_unit": 25.0,
                    "account_id": self.landed_cost.product_tmpl_id.get_product_accounts()["stock_valuation"].id,
                }
            ],
        )

    def test_refund_sign(self):
        """A vendor refund creates landed costs that lower the cost"""
        refund = self._create_bill(move_type="in_refund", invoice_currency_rate=4.0)
        cost_line = self._create_landed_costs(refund).cost_lines
        self.assertEqual(cost_line.price_unit, -25.0)

    def test_receipts_of_the_purchase(self):
        """The landed costs keep the receipts of the purchase that Odoo sets"""
        purchase = self.env["purchase.order"].create(
            {
                "partner_id": self.supplier_id,
                "currency_id": self.other_currency.id,
                "order_line": [
                    Command.create({"product_id": self.product_refrigerator.id, "product_qty": 5, "price_unit": 10})
                ],
            }
        )
        purchase.button_confirm()
        receipt = purchase.picking_ids
        receipt.move_ids.quantity = 5
        receipt.move_ids.picked = True
        receipt.button_validate()
        purchase.action_create_invoice()
        bill = purchase.invoice_ids
        bill.invoice_date = "2026-01-15"
        with Form(bill) as bill_form:
            with bill_form.invoice_line_ids.new() as line:
                line.product_id = self.landed_cost
                line.price_unit = 100.0
                line.tax_ids.clear()
                line.is_landed_costs_line = True
        bill.invoice_currency_rate = 4.0
        bill.action_post()
        landed_costs = self._create_landed_costs(bill)
        self.assertEqual(landed_costs.picking_ids, receipt)
        self.assertEqual(landed_costs.cost_lines.price_unit, 25.0)
