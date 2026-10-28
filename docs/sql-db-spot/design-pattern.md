# sql-db Spot: Design Patterns

Status: EXPERIMENTAL, local only, NOT merged into the core demo, NOT pushed.
Source checked: kristiannordby/sql-db, loaded with load_dataset, 121 rows, train only,
columns question and query only. No real database tables are shipped by that dataset.

## The problem this spot solves

The sql-db pairs are SQL exercises, not governed manager metrics. Copying them
into ARFA_AAPA would break three core rules:

1. The model must not calculate, and the user must not supply free SQL.
2. Every answer must have one written definition, one fixed template, a period,
   and source tables.
3. No customer or owner names, phones, salaries, or passwords may leak, in any
   clause of a query, not only in SELECT.

Therefore the spot does NOT run the original queries. It adapts a small curated
subset into governed metrics, and rejects the rest with a clear abstention.

## Patterns used, and why each one is here

### 1. Adapter Pattern: SqlDbAdapter

The sql-db world speaks: make, sellPrice, sellDate, YEAR(), firstName, lastName.
ARFA_AAPA speaks: one metric key, one definition, one SQLite template, one Answer.

The Adapter is the only place that knows both vocabularies. It translates:
- sellPrice -> sale_price, sellDate -> sale_date, serviceCost -> service_cost
- YEAR(sellDate) = 2022 -> strftime('%Y', sale_date) = '2022'
- An owner-name question -> an aggregate count with no names, or an abstention

Nothing else in the spot imports the original query text at runtime. The original
text lives only in curated.json as audit provenance, never as executable SQL.

### 2. Repository Pattern: SqlDbRepository

All SQLite access goes through one repository, opened read-only (mode=ro).
The repository owns: connection, schema names, and the reference date
(MAX sale_date, MAX service_date). The Facade never touches sqlite3 directly.
This keeps a future real dealership database replaceable without touching
routing, definitions, or the UI: only the repository and the metric templates change.

### 3. Strategy Pattern: GovernedMetric

Each adapted metric is one Strategy object with fixed fields:
metric_key, name_ar, definition_ar, unit, source_tables, sql_template.
The agent routes a question to a metric key, then the strategy runs its template
with parameters only (dealership, year, start, end). No strategy builds SQL from
user words, and no new strategy can be added without a definition and a test.

Curated spot metrics (8, not 121):
- total_cars_sold, average_sell_price, total_sales_revenue
- best_dealership_by_sales_revenue
- cars_serviced_at_least_once, average_service_cost, total_service_cost
- warranty_service_count

Deliberately excluded: owners as an output table, parts, and surveys, because
sql-db contains no parts or survey tables at all, and owner names are PII.

### 4. Facade Pattern: SqlDbSpot

One entry point, ask(question, year=None, dealership=None) -> SpotAnswer.
The Facade hides, in order: normalisation, routing, sensitive-word abstention,
template lookup, whole-statement validation, execution, and answer formatting.
Callers (CLI, web UI, tests) never call the validator or the repository directly.

### 5. Guard / Validator Pattern: SpotValidator

Reuses the core idea from security.py, with a spot-local allowlist:
- Allowed tables only: cars, dealerships, sales, service_records
- SELECT only, one statement only, no semicolon inside the body
- Forbidden anywhere in the whole statement: insert, update, delete, drop,
  alter, create, pragma, attach, password, salary, phone, firstName, lastName,
  customer_name, national_id, and YEAR( (forces the SQLite translation)
A forbidden word in WHERE, JOIN, ORDER BY, or GROUP BY is rejected exactly
like one in SELECT. This is the whole-statement lesson from the earlier
platform audit, applied again here.

### 6. Anti-Corruption Layer: Canonical schema

The spot SQLite schema is canonical, not a copy of the sql-db implied schema:
- All column names are snake_case, all dates are ISO text YYYY-MM-DD
- owner identity is stored only as an anonymised owner_ref integer, never as
  a name, and no spot metric selects it
- serviceCenter is stored as a plain text label, not as a dealership join,
  unless a dealership mapping is explicitly governed later

This layer is what stops a dirty or buggy upstream query, for example the
original join ON c.serialNum = o.ownerID, from ever reaching the database.

### 7. Template Method: ask() flow

Every spot question follows the same fixed steps, in the same order:
normalise -> sensitive check -> route -> template -> validate -> execute ->
format Answer, or abstain with a stated missing reason.
There is no branch where a question bypasses validation, and no branch where
the model invents a number.

## What is NOT a pattern here, on purpose

- No Text-to-SQL generation. The agent never writes SQL from a question.
- No Hugging Face datasets runtime dependency. load_dataset was an inspection
  tool only, in an isolated venv. The spot ships a small vendored curated.json
  and its own deterministic synthetic seed, stdlib only.
- No direct reuse of the 121 original queries as templates. They are reference
  material, audited one by one, and most are rejected.

## Review gate for this spot

Before this spot is merged into the core, or shown to a manager, it needs:
1. Approval of the 8 curated metrics and their definitions
2. Approval of the PII exclusion (no owner names, ever, in this spot)
3. A fresh-clone test run: seed, then tests, then the 8 questions, with numbers
   checked by hand against the seed
4. A decision on parts and surveys: they stay in the core synthetic demo,
   they are NOT claimed to come from sql-db
