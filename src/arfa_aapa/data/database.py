"""Read-only database access for the demo dataset."""

import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = REPO_ROOT / "data" / "demo.db"


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"Demo database not found: {path}. Run: python scripts/seed_demo.py"
        )
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def reference_date(connection: sqlite3.Connection) -> str:
    """Last date present in the demo data. All relative periods anchor to it."""
    row = connection.execute(
        """
        SELECT MAX(d) AS d FROM (
            SELECT MAX(sale_date) AS d FROM sales
            UNION ALL SELECT MAX(opened_date) FROM service_job_cards
            UNION ALL SELECT MAX(sale_date) FROM parts_sales
            UNION ALL SELECT MAX(survey_date) FROM surveys
        )
        """
    ).fetchone()
    if row is None or row["d"] is None:
        raise ValueError("Demo database is empty.")
    return str(row["d"])
