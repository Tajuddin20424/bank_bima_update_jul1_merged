from django.test import SimpleTestCase

from .views import (
    DETAILS_STATEMENT_HEADERS,
    _balance_sql,
    _statement_sql,
    build_statement_filters,
)


class DetailsStatementQueryTests(SimpleTestCase):
    def test_filters_include_main_head_and_inclusive_end_date(self):
        where, params = build_statement_filters("10", "2026-09-01", "2026-09-13")

        self.assertIn("d.tran_type = %s", where)
        self.assertIn("d.tran_date >= %s", where)
        self.assertIn("d.tran_date < DATE_ADD(%s, INTERVAL 1 DAY)", where)
        self.assertEqual(params, ["10", "2026-09-01", "2026-09-13"])

    def test_statement_has_only_requested_columns(self):
        self.assertEqual(DETAILS_STATEMENT_HEADERS, [
            "SL", "Invoice No", "Date", "Main Head", "Product", "Transaction With",
            "Net", "Discount", "Receive", "Payment",
        ])

    def test_statement_uses_payment_mode_and_total_amount(self):
        sql = _statement_sql("1 = 1")

        self.assertIn("LOWER(COALESCE(d.payment_mode, ''))", sql)
        self.assertIn("COALESCE(d.tot_amount, d.amount, 0) AS net_amount", sql)

    def test_balance_query_uses_receive_minus_payment(self):
        sql = _balance_sql("d.tran_type = %s AND d.tran_date < %s")

        self.assertIn("SUM(", sql)
        self.assertIn("CASE", sql)
        self.assertIn("d.receive", sql)
        self.assertIn("d.payment", sql)
        self.assertIn("d.tran_date < %s", sql)
