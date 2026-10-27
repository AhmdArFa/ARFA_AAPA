import json
import tempfile
import unittest
from pathlib import Path

from arfa_aapa.agent import ask
from arfa_aapa.data.seed import build_demo_db

GOLDEN = json.loads((Path(__file__).resolve().parents[1] / "evals" / "golden_questions.json").read_text(encoding="utf-8"))


class TestAgent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.tmp.name) / "demo.db"
        build_demo_db(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_golden_questions_route_correctly(self):
        for item in GOLDEN:
            with self.subTest(question=item["question"]):
                answer = ask(item["question"], db_path=self.db_path)
                self.assertEqual(answer.metric_key, item["expected_metric"])

    def test_confirmed_answer_has_source_and_definition(self):
        answer = ask("ايه ايراد الصيانة اخر 30 يوم؟", db_path=self.db_path)
        self.assertTrue(answer.confirmed)
        self.assertIn("service_job_cards", answer.source_tables)
        self.assertTrue(answer.definition)

    def test_sensitive_question_abstains_without_value(self):
        answer = ask("ايه مرتبات الموظفين؟", db_path=self.db_path)
        self.assertFalse(answer.confirmed)
        self.assertIsNone(answer.metric_key)


if __name__ == "__main__":
    unittest.main()
