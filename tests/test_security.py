import unittest

from arfa_aapa.security import validate_sql


class TestSecurity(unittest.TestCase):
    def test_allows_clean_select(self):
        validate_sql("SELECT branch_id, SUM(amount_egp) FROM sales WHERE status = 'invoiced' GROUP BY branch_id")

    def test_rejects_write(self):
        with self.assertRaises(ValueError):
            validate_sql("UPDATE sales SET amount_egp = 0")

    def test_rejects_unknown_table(self):
        with self.assertRaises(ValueError):
            validate_sql("SELECT * FROM employees")

    def test_rejects_forbidden_column_in_where(self):
        # Whole-statement rule: a clean SELECT list does not save a forbidden WHERE.
        with self.assertRaises(ValueError):
            validate_sql("SELECT branch_id FROM service_job_cards WHERE salary > 0")

    def test_rejects_stacked_statements(self):
        with self.assertRaises(ValueError):
            validate_sql("SELECT * FROM sales; DELETE FROM sales")


if __name__ == "__main__":
    unittest.main()
