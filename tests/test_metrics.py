import tempfile
import unittest
from pathlib import Path

from arfa_aapa.data.database import get_connection
from arfa_aapa.metrics import service_revenue, total_revenue


class TestMetrics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.tmp.name) / "demo.db"
        from arfa_aapa.data.seed import build_demo_db

        build_demo_db(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_revenue_is_positive_and_total_covers_service(self):
        connection = get_connection(self.db_path)
        try:
            service = service_revenue(connection, None, "2026-01-01", "2026-10-27")
            total = total_revenue(connection, None, "2026-01-01", "2026-10-27")
            self.assertGreater(float(service.value), 0)
            self.assertGreaterEqual(float(total.value), float(service.value))
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
