import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hardened import validate_hardened, check_template

GOOD = [
    "SELECT COALESCE(SUM(amount_egp), 0) AS v FROM sales WHERE sale_date BETWEEN :start AND :end AND status = 'invoiced'",
    "SELECT branch_id, COUNT(*) AS v FROM service_job_cards WHERE opened_date BETWEEN :start AND :end GROUP BY branch_id ORDER BY v DESC",
    "SELECT part_name, COALESCE(SUM(stock_qty * unit_price_egp), 0) AS val FROM parts_inventory GROUP BY part_name ORDER BY val DESC LIMIT 100",
    "SELECT COUNT(*) AS v FROM employees WHERE role = 'technician'",
    "SELECT strftime('%Y', sale_date) AS d, SUM(amount_egp) AS v FROM sales GROUP BY d",
]
BAD = [
    "INSERT INTO sales VALUES (1,2,3,4,5,6)",
    "SELECT * FROM sales",
    "SELECT amount_egp FROM sales UNION SELECT amount_egp FROM parts_sales",
    "SELECT amount_egp FROM sales; DROP TABLE sales;",
    "SELECT amount_egp FROM sales WHERE salary > 1000",
    "SELECT amount_egp, phone FROM sales",
    "SELECT amount_egp FROM sales WHERE customer_name = 'x'",
    "SELECT amount_egp FROM sqlite_master",
    "SELECT amount_egp FROM sales WHERE 1=1 -- comment",
    "SELECT amount_egp FROM sales WHERE amount_egp > 0 /* comment */",
    "SELECT amount_egp FROM unknown_table",
    "SELECT secret_col FROM sales",
    "SELECT load_extension('evil') FROM sales",
    "SELECT amount_egp FROM sales WHERE amount_egp IN (SELECT amount_egp FROM employees)",
    "PRAGMA table_info(sales)",
    "SELECT amount_egp FROM sales ATTACH 'x' AS y",
]

class TestHardened(unittest.TestCase):
    def test_good_templates_pass(self):
        for sql in GOOD:
            with self.subTest(sql=sql):
                validate_hardened(sql, audit=False)
    def test_bad_templates_fail(self):
        for sql in BAD:
            with self.subTest(sql=sql):
                with self.assertRaises(ValueError):
                    validate_hardened(sql, audit=False)
    def test_check_template_bool(self):
        self.assertTrue(check_template(GOOD[0]))
        self.assertFalse(check_template(BAD[0]))

if __name__ == "__main__":
    unittest.main()
