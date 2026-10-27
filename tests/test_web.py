import json
import threading
import unittest
import urllib.request

from arfa_aapa.web import create_server


class TestWeb(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Point the web module at a temp demo database by building the real
        # default database first if needed, then use the server as-is.
        # The server reads the default demo.db, which the demo build creates.
        cls.server = create_server(0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _get(self, path):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}") as response:
            return json.loads(response.read().decode("utf-8"))

    def _post(self, path, payload):
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))

    def test_health(self):
        self.assertEqual(self._get("/api/health")["status"], "ok")

    def test_ask_confirmed(self):
        data = self._post("/api/ask", {"question": "ايه اجمالي الايراد اخر 30 يوم؟"})
        self.assertTrue(data["confirmed"])
        self.assertEqual(data["metric_key"], "total_revenue")
        self.assertIn("sales", data["source_tables"])

    def test_ask_abstains(self):
        data = self._post("/api/ask", {"question": "ايه مرتبات الموظفين؟"})
        self.assertFalse(data["confirmed"])
        self.assertIsNone(data["metric_key"])

    def test_kpis(self):
        data = self._get("/api/kpis")
        self.assertEqual(len(data), 4)
        self.assertTrue(all(item["confirmed"] for item in data))


if __name__ == "__main__":
    unittest.main()
