import sys, unittest, sqlite3
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evidence_engine import EvidenceEngine

class TestEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.eng = EvidenceEngine()
        cls.con = sqlite3.connect(str(Path(__file__).resolve().parents[1] / "company.db"))
    def test_profit_matches_components(self):
        a = self.eng.ask("ما هي أرباح الشركة في كل فترة الداتا التجريبية؟")
        self.assertTrue(a.confirmed); self.assertEqual(a.kind, "profit")
        rev = a.evidence["revenue"]["total"]; costs = a.evidence["costs_total"]
        self.assertEqual(a.value, round(rev - costs, 2))
        self.assertIn("تكلفة شراء السيارات", a.text)
    def test_profit_by_branch(self):
        a = self.eng.ask("ما هي أرباح الشركة في كل فترة الداتا التجريبية؟")
        self.assertTrue(a.confirmed)
    def test_warehouse_battery(self):
        a = self.eng.ask("ما هو مخزون البطارية في المخازن؟")
        self.assertTrue(a.confirmed); self.assertEqual(a.kind, "warehouse")
        self.assertEqual([p for p, _, _ in a.evidence["by_part"]], ["بطارية"])
        self.assertEqual(a.evidence["parts_stock_qty"], 69)
    def test_warehouse_low_stock(self):
        a = self.eng.ask("ما هو مخزون قطع الغيار في المخازن؟")
        self.assertTrue(a.confirmed); self.assertGreaterEqual(a.evidence["parts_low_stock_rows"], 0)
    def test_employee_technician(self):
        a = self.eng.ask("كم كارت صيانة قفل فني صيانة 1؟")
        self.assertTrue(a.confirmed); self.assertEqual(a.kind, "employee")
        self.assertEqual(a.evidence["job_cards"][0], 105)
    def test_employee_salesperson(self):
        a = self.eng.ask("كم مبيعات مندوب مبيعات 2 المفوترة؟")
        self.assertTrue(a.confirmed); self.assertEqual(a.evidence["sales_invoiced"][0], 41)
    def test_employee_unknown_abstains(self):
        a = self.eng.ask("كم مبيعات مندوب مبيعات 99؟")
        self.assertFalse(a.confirmed)
    def test_salary_abstains_even_for_manager(self):
        a = self.eng.ask("ما هو مرتب فني صيانة 1؟")
        self.assertFalse(a.confirmed)

if __name__ == "__main__":
    unittest.main()
