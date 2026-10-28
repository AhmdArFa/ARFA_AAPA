"""Local-only demo web UI for the head manager.

Standard library only, no external dependencies.
Binds to 127.0.0.1 only, serves read-only answers from the demo database,
and never touches real company data. This is a demo, not a production
deployment: no login, no multi-user support, no write actions.
"""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .unified_agent import UnifiedAgent

REPO_ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = REPO_ROOT / "web"

KPI_QUESTIONS = [
    "ايه اجمالي الايراد اخر 30 يوم؟",
    "ايه ايراد الصيانة اخر 30 يوم؟",
    "كام كارت شغل مفتوح دلوقتي؟",
    "ايه متوسط رضا العملاء اخر 30 يوم؟",
]


def answer_to_dict(answer) -> dict:
    # UnifiedAnswer has tool/domain/evidence; core Answer has metric_key etc.
    # Map both to the same JSON shape the web UI already renders.
    if hasattr(answer, "tool"):
        ev = answer.evidence or {}
        return {
            "question": answer.question,
            "metric_key": answer.tool,
            "metric_name": ev.get("metric_name") or answer.tool or answer.domain or "",
            "text": answer.text,
            "confirmed": answer.confirmed,
            "period_label": ev.get("period") or "",
            "definition": ev.get("definition") or "",
            "source_tables": list(ev.get("source_tables") or []),
            "missing": answer.missing,
            "value": answer.value,
            "unit": "",
            "detail": "",
        }
    return {
        "question": answer.question,
        "metric_key": answer.metric_key,
        "metric_name": answer.metric_name,
        "text": answer.text,
        "confirmed": answer.confirmed,
        "period_label": answer.period_label,
        "definition": answer.definition,
        "source_tables": list(answer.source_tables),
        "missing": answer.missing,
        "value": answer.value,
        "unit": answer.unit,
        "detail": answer.detail,
    }


def _unified_agent() -> UnifiedAgent:
    return UnifiedAgent()


def kpi_answers() -> list[dict]:
    agent = _unified_agent()
    return [answer_to_dict(agent.ask(question)) for question in KPI_QUESTIONS]


def suggested_questions() -> list[str]:
    golden_path = REPO_ROOT / "evals" / "golden_questions.json"
    items = json.loads(golden_path.read_text(encoding="utf-8"))
    questions = [item["question"] for item in items if item["expected_metric"]]
    # Unified v2 questions, so the UI actually shows profit, warehouse, CRM, employee.
    questions += [
        "ما هي أرباح الشركة في كل فترة الداتا التجريبية؟",
        "ما هو مخزون البطارية في المخازن؟",
        "عدد العملاء المحتملين حسب المصدر في كل فترة الداتا التجريبية",
        "كم كارت صيانة قفل فني صيانة 1؟",
    ]
    return questions


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # Keep demo output clean.
        pass

    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str):
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send_file(WEB_DIR / "index.html", "text/html; charset=utf-8")
        elif self.path == "/api/kpis":
            try:
                self._send_json(kpi_answers())
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=500)
        elif self.path == "/api/questions":
            self._send_json(suggested_questions())
        elif self.path == "/api/health":
            self._send_json({"status": "ok", "demo": True, "read_only": True})
        else:
            self._send_json({"error": "not found"}, status=404)

    def do_POST(self):
        if self.path != "/api/ask":
            self._send_json({"error": "not found"}, status=404)
            return
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except ValueError:
            self._send_json({"error": "invalid JSON"}, status=400)
            return
        question = str(payload.get("question", "")).strip()
        if not question:
            self._send_json({"error": "question is required"}, status=400)
            return
        try:
            self._send_json(answer_to_dict(_unified_agent().ask(question)))
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=500)


def create_server(port: int = 8000) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="ARFA AAPA demo web UI (local only)")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    # Fail fast with a clear message if the demo database is missing.
    # UnifiedAgent prefers data/company.db, otherwise data/demo.db.
    agent = _unified_agent()
    if not agent.db_path.exists():
        raise FileNotFoundError(
            f"Demo database not found: {agent.db_path}. Run: python scripts/seed_demo.py and python scripts/seed_company.py"
        )
    # agent.db_path existence was already checked above; no extra connection needed.
    server = create_server(args.port)
    print(f"ARFA AAPA demo UI running at http://127.0.0.1:{args.port} (local only, demo data only)")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
