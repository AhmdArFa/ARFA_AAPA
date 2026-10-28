import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import CompanyEngine

class TestCompanyEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.eng = CompanyEngine()
    def test_sales_all_period(self):
        a = self.eng.ask("إجمالي إيراد المبيعات في كل فترة الداتا التجريبية")
        self.assertTrue(a.confirmed); self.assertEqual(a.domain, "sales"); self.assertGreater(a.value, 0)
    def test_service_by_type(self):
        a = self.eng.ask("عدد كروت الصيانة حسب نوع الخدمة في كل فترة الداتا التجريبية")
        self.assertTrue(a.confirmed); self.assertEqual(a.domain, "service"); self.assertEqual(sum(v for _, v in a.rows), 420)
    def test_parts(self):
        a = self.eng.ask("إجمالي مبيعات قطع الغيار في كل فترة الداتا التجريبية")
        self.assertTrue(a.confirmed); self.assertEqual(a.domain, "parts")
    def test_survey(self):
        a = self.eng.ask("متوسط رضا العملاء في كل فترة الداتا التجريبية")
        self.assertTrue(a.confirmed); self.assertEqual(a.domain, "survey")
    def test_crm_by_source(self):
        a = self.eng.ask("عدد العملاء المحتملين حسب المصدر في كل فترة الداتا التجريبية")
        self.assertTrue(a.confirmed); self.assertEqual(a.domain, "crm"); self.assertEqual(sum(v for _, v in a.rows), 120)
    def test_accounting_paid(self):
        a = self.eng.ask("إجمالي الفواتير المدفوعة في كل فترة الداتا التجريبية")
        self.assertTrue(a.confirmed); self.assertEqual(a.domain, "accounting")
    def test_cars_available_by_model(self):
        a = self.eng.ask("عدد السيارات المتاحة في المخزون حسب الموديل في كل فترة الداتا التجريبية")
        self.assertTrue(a.confirmed); self.assertEqual(a.domain, "cars")
    def test_salary_abstains(self):
        a = self.eng.ask("ما هي مرتبات الموظفين؟")
        self.assertFalse(a.confirmed)
    def test_hr_domain_abstains(self):
        a = self.eng.ask("إجمالي مبيعات الموارد البشرية في كل فترة الداتا التجريبية")
        self.assertFalse(a.confirmed); self.assertIsNone(a.domain)
    def test_unknown_domain_abstains_and_lists(self):
        a = self.eng.ask("إجمالي مبيعات العقارات في كل فترة الداتا التجريبية")
        self.assertFalse(a.confirmed); self.assertIn("sales", a.text)
    def test_trial_log_records_abstentions(self):
        before = len(self.eng.trial_log)
        self.eng.ask("إجمالي مبيعات العقارات في كل فترة الداتا التجريبية")
        self.assertGreater(len(self.eng.trial_log), before)

if __name__ == "__main__":
    unittest.main()
