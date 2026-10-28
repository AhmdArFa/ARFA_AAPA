"""Read-only query validation, core entry point.

Canonical implementation is src/arfa_aapa/hardened.py. This module is a
thin, backward-compatible wrapper around it, so the old import path
``from arfa_aapa.security import validate_sql`` keeps working, but with
the hardened rules: column and function allowlists, whole-statement
validation, case-insensitive forbidden words, no SELECT *, no UNION,
no subqueries, no comments, and bound parameters only.

The internal reference_date query in data/database.py uses UNION ALL,
but it does NOT go through validate_sql, so it is unaffected.
"""

from .hardened import ALLOWED_COLUMNS, FORBIDDEN_WORDS, validate_hardened

ALLOWED_TABLES = set(ALLOWED_COLUMNS.keys())


def validate_sql(sql: str) -> None:
    """Raise ValueError if the SQL is not a single safe SELECT."""
    validate_hardened(sql, audit=True)  # audit=True: rejected templates go to rejected.log, gitignored
