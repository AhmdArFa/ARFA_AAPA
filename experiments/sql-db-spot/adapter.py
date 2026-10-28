"""sql-db Spot: Adapter, Repository, Validator, Facade. Stdlib only.

This spot is experimental and separate from the core demo in src/arfa_aapa/.
It does NOT run original sql-db queries, does NOT call Hugging Face at runtime,
and does NOT select owner names. See docs/sql-db-spot/design-pattern.md.
"""
import json, re, sqlite3
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
ALLOWED_TABLES = {"cars", "dealerships", "sales", "service_records"}
FORBIDDEN = {"insert", "update", "delete", "drop", "alter", "create", "truncate",
             "replace", "attach", "detach", "pragma", "vacuum", "password", "salary",
             "phone", "customer_name", "national_id", "firstname", "lastname", "year("}
_TABLE_RE = re.compile(r"\b(?:from|join)\s+([a-z_][a-z0-9_]*)", re.IGNORECASE)
_WORD_RE = re.compile(r"[a-z_][a-z0-9_]*")

def validate_spot_sql(sql: str) -> None:
    text = sql.strip()
    if not text.lower().startswith("select"):
        raise ValueError("Only SELECT statements are allowed.")
    body = text[:-1].strip() if text.endswith(";") else text
    if ";" in body:
        raise ValueError("Only one statement is allowed.")
    if "year(" in body.lower():
        raise ValueError("YEAR() is forbidden in the spot. Use strftime('%Y', date) instead.")
    words = {w.lower() for w in _WORD_RE.findall(body)}
    bad = words & FORBIDDEN
    if bad:
        raise ValueError(f"Forbidden words in query: {sorted(bad)}")
    tables = _TABLE_RE.findall(body)
    if not tables:
        raise ValueError("Query must reference at least one allowed table.")
    unknown = [t for t in tables if t.lower() not in ALLOWED_TABLES]
    if unknown:
        raise ValueError(f"Unknown or disallowed tables: {unknown}")

@dataclass(frozen=True)
class SpotMetric:
    key: str
    name: str
    definition: str
    unit: str
    source_tables: tuple
    template: str

def load_metrics() -> dict:
    data = json.loads((HERE / "curated.json").read_text())
    out = {}
    for m in data["adapted"]:
        out[m["metric_key"]] = SpotMetric(m["metric_key"], m["metric_key"], m["definition"],
                                          m["unit"], tuple(m["source_tables"]), m["template"])
    return out

class SqlDbRepository:
    """Read-only repository. Only this class touches sqlite3."""
    def __init__(self, db_path: Path | None = None):
        self.path = Path(db_path) if db_path else HERE / "spot.db"
        if not self.path.exists():
            raise FileNotFoundError(f"Spot database not found: {self.path}. Run: python3 seed.py")
    def run(self, sql: str, params: dict):
        validate_spot_sql(sql)
        con = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        try:
            return con.execute(sql, params).fetchall()
        finally:
            con.close()

@dataclass
class SpotAnswer:
    question: str
    metric_key: str | None
    confirmed: bool
    text: str
    value: object = None
    unit: str = ""
    definition: str = ""
    source_tables: tuple = ()
    missing: str = ""

def _norm(text: str) -> str:
    return re.sub(r"[^\w\s]", " ", text.lower())

class SqlDbSpot:
    """Facade: the only entry point for spot questions."""
    SENSITIVE = ["owner", "firstname", "lastname", "phone", "salary", "password", "مالك", "صاحب"]
    def __init__(self, db_path: Path | None = None):
        self.repo = SqlDbRepository(db_path)
        self.metrics = load_metrics()
    def _route(self, q: str) -> str | None:
        if "best dealership" in q or "highest total sales revenue" in q:
            return "best_dealership_by_sales_revenue"
        if "total sales revenue" in q or "total revenue" in q:
            return "total_sales_revenue"
        if "average price" in q or "average sell" in q:
            return "average_sell_price"
        if "total number of sales" in q or "how many sales" in q or "total cars sold" in q:
            return "total_cars_sold"
        if "serviced at least once" in q:
            return "cars_serviced_at_least_once"
        if "average service cost" in q:
            return "average_service_cost"
        if "total service cost" in q:
            return "total_service_cost"
        if "warranty" in q:
            return "warranty_service_count"
        return None
    def ask(self, question: str, year: str | None = None, center: str | None = None) -> SpotAnswer:
        q = _norm(question)
        if any(w in q for w in self.SENSITIVE):
            return SpotAnswer(question, None, False,
                "Abstention: owner names and personal data are excluded from this spot.",
                missing="Owner names are excluded from this spot.")
        key = self._route(q)
        if key is None:
            return SpotAnswer(question, None, False,
                "Abstention: this question is not mapped to a curated spot metric.",
                missing="No curated spot metric for this question.")
        m = self.metrics[key]
        params = {"year": year or "2022", "center": center}
        rows = self.repo.run(m.template, params)
        if not rows:
            return SpotAnswer(question, key, False, "Abstention: no data for this metric.", missing="No data.")
        row = rows[0]
        if key == "best_dealership_by_sales_revenue":
            value, detail = row["name"], f"revenue {round(float(row['v']), 2)}"
            text = f"{key} in {params['year']}: {value} ({detail} {m.unit}). Definition: {m.definition} Source: {', '.join(m.source_tables)}."
            return SpotAnswer(question, key, True, text, value, m.unit, m.definition, m.source_tables, detail)
        value = row["v"]
        if isinstance(value, float):
            value = round(value, 2)
        text = f"{key}: {value} {m.unit}. Definition: {m.definition} Source: {', '.join(m.source_tables)}."
        return SpotAnswer(question, key, True, text, value, m.unit, m.definition, m.source_tables)

if __name__ == "__main__":
    spot = SqlDbSpot()
    for q, kw in [
        ("What is the total sales revenue in 2022?", {"year": "2022"}),
        ("Which dealership had the highest total sales revenue in 2021?", {"year": "2021"}),
        ("What is the average price of cars sold?", {}),
        ("How many cars have been serviced at least once?", {}),
        ("Find the owner who has registered the most cars.", {}),
        ("List all unique car makes available.", {}),
    ]:
        a = spot.ask(q, **kw)
        print(f"{'CONFIRMED' if a.confirmed else 'ABSTAIN'} | {a.metric_key} | {a.text}")
