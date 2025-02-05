from odoo.tests.common import TransactionCase


class TestStockBook(TransactionCase):
    def setUp(self):
        super(TestStockBook, self).setUp()
        self.StockBook = self.env["stock.book"]
        self.IrSequence = self.env["ir.sequence"]
        self.ResCompany = self.env["res.company"]

        self.sequence = self.IrSequence.create(
            {
                "name": "Test Sequence",
                "code": "stock.voucher",
                "prefix": "TEST-",
                "padding": 5,
                "implementation": "no_gap",
            }
        )

        self.company = self.ResCompany.create(
            {
                "name": "Test Company",
            }
        )

    def test_create_stock_book(self):
        stock_book = self.StockBook.create(
            {
                "name": "Test Stock Book",
                "sequence_id": self.sequence.id,
                "lines_per_voucher": 10,
                "company_id": self.company.id,
            }
        )
        self.assertTrue(stock_book)
        self.assertEqual(stock_book.name, "Test Stock Book")
        self.assertEqual(stock_book.sequence_id, self.sequence)
        self.assertEqual(stock_book.lines_per_voucher, 10)
        self.assertEqual(stock_book.company_id, self.company)
