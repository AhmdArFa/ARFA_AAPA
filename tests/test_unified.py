import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from arfa_aapa.unified_agent import UnifiedAgent
from arfa_aapa.tools import TOOLS, get_tool
from arfa_aapa.hardened import validate_hardened


class TestUnifiedAgent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        repo = Path(__file__).resolve().parents[1]
        company_db = repo / "data" / "company.db"
        if not company_db.exists():
            import subprocess
            subprocess.run([sys.executable, str(repo / "scripts" / "seed_company.py")],
                           check=True, cwd=str(repo))
        cls.agent = UnifiedAgent()

    def test_core_total_revenue(self):
        a = self.agent.ask("إجمالي الإيراد في آخر 30 يوم")
        self.assertTrue(a.confirmed)
        self.assertEqual(a.value, 18352310.0)

    def test_sales_revenue_specific(self):
        a = self.agent.ask("ايه ايراد مبيعات السيارات الشهر اللي فات؟")
        self.assertTrue(a.confirmed)

    def test_crm_by_source(self):
        a = self.agent.ask("عدد العملاء المحتملين حسب المصدر في كل فترة الداتا التجريبية")
        self.assertTrue(a.confirmed)
        self.assertEqual(a.tool, "crm")

    def test_profit_with_evidence(self):
        a = self.agent.ask("ما هي أرباح الشركة في كل فترة الداتا التجريبية؟")
        self.assertTrue(a.confirmed)
        self.assertEqual(a.tool, "company_profit")
        self.assertIn("تكلفة شراء السيارات", a.text)
        self.assertEqual(a.value, 113434104.0)

    def test_warehouse_battery(self):
        a = self.agent.ask("ما هو مخزون البطارية في المخازن؟")
        self.assertTrue(a.confirmed)
        self.assertEqual(a.tool, "warehouse_stock")

    def test_employee_technician(self):
        a = self.agent.ask("كم كارت صيانة قفل فني صيانة 1؟")
        self.assertTrue(a.confirmed)
        self.assertEqual(a.tool, "employee_performance")

    def test_salary_abstains(self):
        a = self.agent.ask("ما هو مرتب فني صيانة 1؟")
        self.assertFalse(a.confirmed)

    def test_injection_abstains_and_db_survives(self):
        a = self.agent.ask("إجمالي الإيراد'; DROP TABLE sales; --")
        self.assertFalse(a.confirmed)
        b = self.agent.ask("إجمالي الإيراد في آخر 30 يوم")
        self.assertTrue(b.confirmed)
        self.assertEqual(b.value, 18352310.0)

    def test_unknown_domain_abstains(self):
        a = self.agent.ask("إجمالي مبيعات العقارات في كل فترة الداتا التجريبية")
        self.assertFalse(a.confirmed)

    def test_tools_registry(self):
        self.assertGreaterEqual(len(TOOLS), 10)
        for tool in TOOLS:
            self.assertTrue(tool.name)
            self.assertTrue(tool.description_ar)
            self.assertTrue(tool.parameters is not None)
        self.assertIsNotNone(get_tool("company_profit"))
        self.assertIsNotNone(get_tool("warehouse_stock"))
        self.assertIsNotNone(get_tool("employee_performance"))

    def test_skills_files_exist(self):
        root = Path(__file__).resolve().parents[1] / "skills"
        for skill in ["answer_with_evidence", "profit_analysis", "warehouse_check",
                      "employee_performance", "trial_mode", "security_guard"]:
            p = root / skill / "SKILL.md"
            self.assertTrue(p.exists(), f"missing skill {skill}")
            text = p.read_text()
            self.assertIn("Forbidden", text)

    def test_hardened_validator_blocks_all_caps(self):
        with self.assertRaises(ValueError):
            validate_hardened("SELECT amount_egp FROM sales ATTACH 'x' AS y", audit=False)
        with self.assertRaises(ValueError):
            validate_hardened("SELECT * FROM sales", audit=False)


if __name__ == "__main__":
    unittest.main()

class TestCanonicalSource(unittest.TestCase):
    def test_security_is_hardened(self):
        from arfa_aapa.security import validate_sql
        with self.assertRaises(ValueError):
            validate_sql("SELECT amount_egp FROM sales ATTACH 'x' AS y")
        with self.assertRaises(ValueError):
            validate_sql("SELECT * FROM sales")
        validate_sql("SELECT branch_id, SUM(amount_egp) FROM sales WHERE status = 'invoiced' GROUP BY branch_id")
    def test_experiments_wrapper_matches_src(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments" / "security-hardened"))
        import hardened as exp_hardened
        from arfa_aapa.hardened import validate_hardened
        self.assertIs(exp_hardened.validate_hardened, validate_hardened)
