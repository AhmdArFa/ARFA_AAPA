"""Hardened data rules, defense in depth. Stdlib only.

This is EXPERIMENTAL and stricter than src/arfa_aapa/security.py.
It is the reference validator for the maintenance guide in
docs/SECURITY_AND_MAINTENANCE.md. It does NOT replace the core validator
until a review gate approves the migration, because it rejects some
previously allowed shapes (SELECT *, UNION, unknown functions).

Layers, in order:
0. Input hygiene: no null bytes, no control characters except newline/tab.
1. No comments, no stacked statements, no semicolon inside the body.
2. SELECT only, one statement, no UNION / EXCEPT / INTERSECT.
3. Whole-statement forbidden words, including sensitive columns, in ANY clause.
4. Table allowlist, with table aliases resolved to real tables.
5. Column allowlist, per table, whole statement, with string literals blanked
   first, so a literal containing the word FROM cannot cause a false pass or fail.
6. Function allowlist: only aggregate and date helpers used by governed templates.
7. No SELECT *, no table.*, no sqlite_master, no pragma, no attach, no load_extension.
8. Parameters only for values: this validator checks templates, it never
   substitutes user text into SQL. Callers must use bound parameters.
9. Read-only execution is a separate layer: open SQLite with mode=ro and
   PRAGMA query_only = ON, and cap breakdown rows at 100 in the repository.
10. Audit: every rejected template is logged with template hash, reason,
    and role, never with a password or personal value.
"""
import hashlib, re
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Table -> allowed columns. If a column is not listed here, it cannot be
# selected, filtered, joined, ordered, or grouped by, anywhere.
ALLOWED_COLUMNS = {
    "branches": {"id", "name", "city"},
    "sales": {"id", "branch_id", "sale_date", "vehicle_model", "amount_egp", "status", "salesperson_id"},
    "service_job_cards": {"id", "branch_id", "opened_date", "closed_date", "status", "service_type", "labor_amount_egp", "sold_hours", "actual_hours", "technician_id"},
    "parts_sales": {"id", "branch_id", "sale_date", "part_name", "quantity", "amount_egp"},
    "parts_inventory": {"id", "branch_id", "part_name", "stock_qty", "reorder_level", "unit_price_egp"},
    "surveys": {"id", "branch_id", "survey_date", "score_1_5"},
    "crm_leads": {"id", "branch_id", "created_date", "source", "status"},
    "accounting_invoices": {"id", "branch_id", "invoice_date", "amount_egp", "status"},
    "accounting_costs": {"id", "branch_id", "cost_date", "category", "amount_egp"},
    "cars_inventory": {"id", "branch_id", "vehicle_model", "status", "price_egp"},
    "employees": {"id", "name", "role", "branch_id"},
    "dealerships": {"dealership_id", "name", "state", "year_established", "num_employees"},
    "cars": {"serial_num", "make", "model", "mpg", "total_miles"},
    "service_records": {"service_id", "serial_num", "service_center", "service_type", "service_cost", "service_date", "warranty_covered", "service_manager_ref"},
}
ALLOWED_FUNCTIONS = {"count", "sum", "avg", "min", "max", "coalesce", "strftime", "substr", "date", "abs", "round", "case", "when", "then", "else", "end", "cast"}
FORBIDDEN_WORDS = {
    # Writes and schema changes
    "insert", "update", "delete", "drop", "alter", "create", "truncate", "replace",
    "attach", "detach", "pragma", "vacuum", "reindex", "analyze",
    # SQLite internals and extensions
    "load_extension", "sqlite_master", "sqlite_sequence",
    # Set operations that can smuggle a second query shape
    "union", "except", "intersect",
    # Sensitive columns and credentials, in any clause, any spelling variant
    "password", "salary", "phone", "customer_name", "national_id", "firstname", "lastname",
    "owner_name", "email", "address", "ssn", "credit_card",
    # Dangerous functions
    "randomblob", "zeroblob", "hex", "glob", "like",
}
SQL_KEYWORDS = {"select", "from", "join", "left", "inner", "outer", "on", "where", "and", "or", "not", "in", "is", "null",
                "between", "group", "by", "order", "asc", "desc", "limit", "distinct", "as", "case", "when", "then", "else", "end",
                "cast", "true", "false"}
_WORD_RE = re.compile(r"[a-z_][a-z0-9_]*", re.IGNORECASE)  # CASE BUG FIX: all-caps ATTACH/UNION previously bypassed the old validator
_FUNC_RE = re.compile(r"([a-z_][a-z0-9_]*)\s*\(")
_TABLE_RE = re.compile(r"\b(?:from|join)\s+([a-z_][a-z0-9_]*)(?:\s+(?:as\s+)?([a-z_][a-z0-9_]*))?", re.IGNORECASE)

def _blank_literals(sql: str) -> str:
    # Replace '...' and "..." literals with '' so words inside literals
    # cannot hide a forbidden column, and cannot cause a false rejection.
    return re.sub(r"'[^']*'|\"[^\"]*\"", "''", sql)

def _audit(reason: str, sql: str, role: str = "head_manager"):
    try:
        h = hashlib.sha256(sql.encode()).hexdigest()[:16]
        line = f"{datetime.now(timezone.utc).isoformat()} role={role} template_hash={h} rejected={reason}\n"
        with open(HERE / "rejected.log", "a") as f:
            f.write(line)
    except OSError:
        pass

def validate_hardened(sql: str, role: str = "head_manager", audit: bool = True) -> None:
    """Raise ValueError on any unsafe shape. Fail closed: unknown = rejected."""
    def fail(reason: str):
        if audit: _audit(reason, sql, role)
        raise ValueError(reason)
    if not sql or not sql.strip():
        fail("Empty query.")
    if "\x00" in sql:
        fail("Null byte in query.")
    if any(ord(c) < 32 and c not in "\n\t\r" for c in sql):
        fail("Control character in query.")
    if "--" in sql or "/*" in sql or "*/" in sql:
        fail("SQL comments are forbidden.")
    text = sql.strip()
    if not text.lower().startswith("select"):
        fail("Only SELECT statements are allowed.")
    body = text[:-1].strip() if text.endswith(";") else text
    if ";" in body:
        fail("Only one statement is allowed.")
    if re.search(r"SELECT\s+\*|\.\*", body, re.IGNORECASE):
        # SELECT * and table.* are forbidden: explicit columns only.
        # COUNT(*) and stock_qty * unit_price_egp are allowed, they are not wildcards.
        fail("Wildcard * is forbidden. Use explicit allowed columns only.")
    if len(re.findall(r"\bselect\b", body, re.IGNORECASE)) > 1:
        # No subqueries and no UNION second SELECT in user-facing templates.
        # Governed templates are flat SELECTs; internal reference_date is not user-facing.
        fail("Nested SELECTs and UNION second SELECTs are forbidden.")
    blank = _blank_literals(body)
    words = {w.lower() for w in _WORD_RE.findall(blank)}
    bad = words & FORBIDDEN_WORDS
    if bad:
        fail(f"Forbidden words in query: {sorted(bad)}")
    # Functions: every word followed by ( must be allowed
    funcs = {f.lower() for f in _FUNC_RE.findall(blank)}
    # CASE/WHEN are handled by the function list above; other keywords are not functions
    unknown_funcs = {f for f in funcs if f not in ALLOWED_FUNCTIONS and f not in SQL_KEYWORDS}
    if unknown_funcs:
        fail(f"Unknown or disallowed functions: {sorted(unknown_funcs)}")
    # Tables and aliases
    tables = _TABLE_RE.findall(blank)
    if not tables:
        fail("Query must reference at least one allowed table.")
    alias_to_table = {}
    real_tables = []
    for table, alias in tables:
        table = table.lower()
        if table not in ALLOWED_COLUMNS:
            fail(f"Unknown or disallowed table: {table}")
        real_tables.append(table)
        if alias and alias.lower() not in SQL_KEYWORDS:
            alias_to_table[alias.lower()] = table
    # Columns: every identifier that is not a keyword, function, table, alias,
    # or alias-qualified prefix must be an allowed column for a referenced table.
    # This is the whole-statement pass: WHERE, JOIN ON, ORDER BY, GROUP BY included.
    allowed_cols = set()
    for t in real_tables:
        allowed_cols |= ALLOWED_COLUMNS[t]
    # Remove table names, aliases, keywords, functions from candidate words
    candidates = words - SQL_KEYWORDS - ALLOWED_FUNCTIONS - set(real_tables) - set(alias_to_table.keys())
    # Also remove the literal 'v', 'n', 'd' output aliases used by templates? No:
    # output aliases must be checked too, so they are NOT exempted here, except
    # the fixed aliases used in governed templates, which are registered below.
    candidates -= {"v", "n", "d", "qty", "val", "low"}
    # Remove qualified column prefixes: table.column and alias.column
    for m in re.finditer(r"\b([a-z_][a-z0-9_]*)\.([a-z_][a-z0-9_]*)", blank):
        prefix, col = m.group(1).lower(), m.group(2).lower()
        if prefix in alias_to_table:
            expected = alias_to_table[prefix]
            if col not in ALLOWED_COLUMNS[expected]:
                fail(f"Column {col} is not allowed for table {expected}.")
        elif prefix in ALLOWED_COLUMNS:
            if col not in ALLOWED_COLUMNS[prefix]:
                fail(f"Column {col} is not allowed for table {prefix}.")
        else:
            fail(f"Unknown table or alias prefix: {prefix}.")
        candidates.discard(prefix); candidates.discard(col)
    # Output aliases after AS are not columns (branch_name, total_sales, etc.).
    as_aliases = set(re.findall(r"\bAS\s+([a-z_][a-z0-9_]*)", blank, re.IGNORECASE))
    candidates -= {a.lower() for a in as_aliases}
    # Bound parameters (:start, :end, :branch_id, :year, :center) are not columns.
    param_names = set(re.findall(r":([a-z_][a-z0-9_]*)", blank))
    candidates -= param_names
    unknown_cols = {c for c in candidates if c not in allowed_cols}
    # Words that are string-literal values in templates, like 'invoiced', 'paid',
    # are already blanked, so any remaining unknown word is a column or a keyword.
    if unknown_cols:
        fail(f"Unknown or disallowed columns: {sorted(unknown_cols)}")
    # Role scope, head manager only in this prototype: other roles are rejected
    # at the registry level, not here, but the validator records the role.
    if role not in ("head_manager",):
        fail(f"Role {role} is not allowed for direct query validation in this prototype.")

def check_template(sql: str) -> bool:
    try:
        validate_hardened(sql, audit=False); return True
    except ValueError:
        return False
