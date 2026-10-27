"""Read-only query validation.

The rule is simple and strict: validation runs on the whole statement,
not only on the SELECT list. A forbidden column in WHERE, JOIN, ORDER BY
or GROUP BY is rejected exactly like one in SELECT.
"""

import re

ALLOWED_TABLES = {
    "branches",
    "sales",
    "service_job_cards",
    "parts_sales",
    "parts_inventory",
    "surveys",
}

FORBIDDEN_WORDS = {
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "truncate",
    "replace",
    "attach",
    "detach",
    "pragma",
    "vacuum",
    # Sensitive columns that must never appear anywhere in a query.
    "password",
    "salary",
    "phone",
    "customer_name",
    "national_id",
}

_TABLE_RE = re.compile(r"\b(?:from|join)\s+([a-z_][a-z0-9_]*)", re.IGNORECASE)
_WORD_RE = re.compile(r"[a-z_][a-z0-9_]*")


def validate_sql(sql: str) -> None:
    """Raise ValueError if the SQL is not a single safe SELECT."""
    text = sql.strip()
    if not text.lower().startswith("select"):
        raise ValueError("Only SELECT statements are allowed.")
    body = text[:-1].strip() if text.endswith(";") else text
    if ";" in body:
        raise ValueError("Only one statement is allowed.")
    words = set(word.lower() for word in _WORD_RE.findall(body))
    forbidden = words & FORBIDDEN_WORDS
    if forbidden:
        raise ValueError(f"Forbidden words in query: {sorted(forbidden)}")
    tables = _TABLE_RE.findall(body)
    if not tables:
        raise ValueError("Query must reference at least one allowed table.")
    unknown = [table for table in tables if table.lower() not in ALLOWED_TABLES]
    if unknown:
        raise ValueError(f"Unknown or disallowed tables: {unknown}")
