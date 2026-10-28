import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adapter import SqlDbSpot, validate_spot_sql

class TestSpot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spot = SqlDbSpot()
    def test_total_sales_revenue_2022(self):
        a = self.spot.ask("What is the total sales revenue in 2022?", year="2022")
        self.assertTrue(a.confirmed)
        # seed: 18 sales in 2022, prices 20000 + (i%5)*1000, i=12..29
        expected = sum(20000 + (i % 5) * 1000 for i in range(12, 30))
        self.assertEqual(a.value, expected)
    def test_average_sell_price(self):
        a = self.spot.ask("What is the average price of cars sold?")
        self.assertTrue(a.confirmed)
        self.assertEqual(a.value, 22000.0)
    def test_cars_serviced(self):
        a = self.spot.ask("How many cars have been serviced at least once?")
        self.assertTrue(a.confirmed)
        self.assertEqual(a.value, 10)
    def test_warranty_count(self):
        a = self.spot.ask("How many warranty services are there?")
        self.assertTrue(a.confirmed)
        self.assertEqual(a.value, 10)
    def test_owner_question_abstains(self):
        a = self.spot.ask("Find the owner who has registered the most cars.")
        self.assertFalse(a.confirmed)
        self.assertIsNone(a.metric_key)
    def test_unmapped_question_abstains(self):
        a = self.spot.ask("List all unique car makes available.")
        self.assertFalse(a.confirmed)
    def test_year_forbidden(self):
        with self.assertRaises(ValueError):
            validate_spot_sql("SELECT COUNT(*) FROM sales WHERE YEAR(sale_date) = 2022")
    def test_insert_forbidden(self):
        with self.assertRaises(ValueError):
            validate_spot_sql("INSERT INTO sales VALUES (1,2,3,4,5,6,7,8)")
    def test_owner_table_forbidden(self):
        with self.assertRaises(ValueError):
            validate_spot_sql("SELECT firstName FROM owners")
    def test_unknown_table_forbidden(self):
        with self.assertRaises(ValueError):
            validate_spot_sql("SELECT * FROM parts_sales")

if __name__ == "__main__":
    unittest.main()
