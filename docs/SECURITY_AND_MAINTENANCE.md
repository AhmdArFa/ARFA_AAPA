# Security and Maintenance Guide

Status: 2026-10-28, local version, part of the push after the unified agent tests.
Scope: ARFA_AAPA, head-manager Business Q and A, demo and experimental engines.
Golden rule, unchanged: the database calculates, the agent only explains.
No invented numbers, no free SQL from the user, no PII leak, no guess.

## 1. Threat model

Who can try to break it, and how:

- A trial user types a question that is really an instruction, for example
  a question containing a quote, a semicolon, a comment, or a second statement.
- A question mentions a sensitive field, for example salary, phone, customer
  name, national ID, or password, in the question, in a filter, or in a sort.
- A question tries to reach a table or column that is not in the manager scope,
  through WHERE, JOIN ON, ORDER BY, GROUP BY, or an output alias, not only
  through SELECT. This exact hole was found and fixed in the earlier platform
  audit: a SELECT-only allowlist let unlisted columns be probed through WHERE.
- A question tries to use a function, a subquery, a UNION, or sqlite_master
  to smuggle a second query shape.
- A future code change adds a column, for example salary to employees, and an
  old SELECT * query suddenly returns it. This is why SELECT * is forbidden.
- A future code change adds a table, a metric, or a domain, but forgets to
  update the allowlist, the seed, the tests, or the verified numbers in docs.

The manager in the trial is trusted to ask business questions, but not trusted
to write SQL. The agent, the model, and any external question list are also
not trusted to write SQL. Only governed templates in code are trusted, and
only after validation.

## 2. Audit findings, 2026-10-28

Found by reading every execute call in the repo, not by guessing:

- Core `src/arfa_aapa/security.py`: table allowlist only, no column allowlist,
  no function allowlist, allows SELECT *, UNION, subqueries, and comments.
  Case bug: its word regex is lowercase only, so an all-caps word such as
  ATTACH, UNION, or SALARY can bypass the forbidden-word check. This is fixed
  in the hardened validator, not yet in the core validator.
- Company engine `experiments/company-domains/engine.py`: builds SQL from a
  registry, which is safe in principle, but had no validator choke point at all.
  Its templates are now checked by the hardened validator in tests.
- Evidence engine `experiments/company-domains/evidence_engine.py`: used
  SELECT * FROM employees. Fixed 2026-10-28 to explicit columns
  id, name, role, branch_id. If a salary column is ever added to employees,
  SELECT * would have leaked it. This is the canonical example for rule 7.
- Spot adapter `experiments/sql-db-spot/adapter.py`: has a table allowlist,
  but no column allowlist, same as the core.
- All engines open SQLite read-only with mode=ro. That is layer 4, not a
  replacement for validation, because a read-only SELECT can still leak a
  sensitive column if the column is allowed.

## 3. Complex rules, hardened validator

Reference implementation, experimental, not yet the core validator:
`experiments/security-hardened/hardened.py`, tests in
`experiments/security-hardened/tests/test_hardened.py`.
It is stricter than the core, on purpose. Migration to the core is a separate
review gate, see section 8.

Rules, in order, fail closed, unknown means rejected:

0. Input hygiene: no null bytes, no control characters except newline and tab.
1. No SQL comments: no --, no /*, no */. Comments are a classic injection hideout.
2. SELECT only, one statement only, no semicolon inside the body. A trailing
   semicolon is stripped, then any remaining semicolon rejects.
3. No SELECT *, no table.*. Explicit allowed columns only. COUNT(*) and
   stock_qty * unit_price_egp are allowed, they are not wildcards.
4. No nested SELECT, no UNION, EXCEPT, or INTERSECT second SELECT.
   Governed templates are flat SELECTs. The core reference_date UNION is
   internal, not user-facing, and must stay out of this validator.
5. Whole-statement forbidden words, case-insensitive, in ANY clause:
   insert, update, delete, drop, alter, create, truncate, replace, attach,
   detach, pragma, vacuum, reindex, analyze, load_extension, sqlite_master,
   sqlite_sequence, union, except, intersect, randomblob, zeroblob, hex, glob,
   like, and sensitive words: password, salary, phone, customer_name,
   national_id, firstname, lastname, owner_name, email, address, ssn, credit_card.
   A forbidden word in WHERE, JOIN ON, ORDER BY, GROUP BY, or an alias rejects
   exactly like one in SELECT.
6. Table allowlist, with aliases resolved to real tables. Unknown table rejects.
7. Column allowlist, per table, whole statement, with string literals blanked
   first, so a literal containing the word FROM cannot hide or cause a false
   rejection. Qualified columns table.column and alias.column are checked
   against that table. Unqualified columns must be in at least one referenced
   table. Output aliases after AS are exempted, because they are not columns.
   Bound parameters :start, :end, :branch_id, :year, :center are not columns.
8. Function allowlist only: count, sum, avg, min, max, coalesce, strftime,
   substr, date, abs, round, case, when, then, else, end, cast.
   Any other word followed by ( rejects.
9. Parameters only for values: user text never enters SQL by string formatting.
   Table names, column names, measures, and dimensions come only from the
   registry in code. Branch is an integer from a fixed mapping, never a string
   from the question. Part name comes from a fixed list, never from free text.
   Employee name comes from a fixed demo list, matched exactly, never from
   free text used as a filter value without binding.
10. Read-only execution: open with mode=ro, set PRAGMA query_only = ON in the
    repository layer, cap breakdown rows at 100, and set a query timeout in
    production. The demo repository uses mode=ro today; query_only and the row
    cap are in the hardened repository checklist, not yet in every engine.
11. Role scope: head manager only in this prototype. Other roles must be
    enforced at the registry level, not in a prompt: a role that may see only
    its own module must never receive a template for another module, even if
    the validator would allow the table.
12. Audit: every rejected template is logged to experiments/security-hardened/
    rejected.log with timestamp, role, template hash (SHA-256, first 16 hex),
    and reason, never with a password or personal value. A rejected attempt
    returns an abstention to the user, never the database error text.

Allowed example:
SELECT COALESCE(SUM(amount_egp), 0) AS v FROM sales
WHERE sale_date BETWEEN :start AND :end AND status = 'invoiced'

Rejected examples, all covered by tests:
SELECT * FROM sales
SELECT amount_egp FROM sales UNION SELECT amount_egp FROM parts_sales
SELECT amount_egp FROM sales; DROP TABLE sales;
SELECT amount_egp FROM sales WHERE salary > 1000
SELECT amount_egp, phone FROM sales
SELECT amount_egp FROM sqlite_master
SELECT amount_egp FROM sales WHERE 1=1 -- comment
SELECT amount_egp FROM sales ATTACH 'x' AS y
SELECT amount_egp FROM unknown_table
SELECT secret_col FROM sales
SELECT load_extension('evil') FROM sales
PRAGMA table_info(sales)

## 4. What is allowed, per domain, in the demo

- Core 4S: branches, sales, service_job_cards, parts_sales, parts_inventory,
  surveys. See src/arfa_aapa/metrics.py for the 11 governed metrics.
- Company domains: plus crm_leads, accounting_invoices, accounting_costs,
  cars_inventory, employees. See experiments/company-domains/engine.py and
  evidence_engine.py.
- Spot: cars, dealerships, sales, service_records, with a different sales
  table shape. Spot and core sales tables must never be mixed in one query.
- Employees, demo only: id, name, role, branch_id. No salary, phone,
  national ID, or password column exists in the demo. If such a column is
  ever added, it must NOT be added to the hardened allowlist without a
  separate, audited, head-manager-only metric and an explicit approval.
- Profit, demo only: invoiced revenue minus recorded demo costs.
  Car purchase cost is NOT in the demo costs, so demo profit is NOT net
  profit. Every profit answer must carry that caveat, with revenue by source
  and costs by category, or it must not be shown.

## 5. Cross-file impact map

Read this before any fix or update. A change in one file almost always
breaks another file, a test, or a verified number in docs.

| If you change | You must check | Tests to run | Docs and numbers to update |
|---|---|---|---|
| security.py or hardened.py allowlist | metrics.py, engine.py, evidence_engine.py, adapter.py, every template that uses a new table or column | test_security, test_hardened, test_metrics, test_engine, test_evidence, test_spot, test_unified | docs/SECURITY_AND_MAINTENANCE.md, section 3 and 4 |
| A metric template in metrics.py | agent.py routing, web.py KPIs, golden_questions.json, README metric table | test_metrics, test_agent, test_web, test_unified | docs/metrics.md, README, deck numbers if the metric is on a slide |
| Agent routing in agent.py or unified_agent.py | golden_questions.json, web/index.html suggested questions, tools.py registry, skills/ | test_agent, test_web, test_unified | docs/architecture.md, README endpoints |
| Seed in data/seed.py or seed_company.py | Every verified number: core revenue, open and overdue cards, satisfaction, spot numbers, company numbers, profit, warehouse, employee totals | All tests, then recompute numbers by running the seed and the demo CLI | README, docs/metrics.md, deck, any answer example in docs |
| Schema, a new table or column | security allowlist, hardened allowlist, seed, metrics, engine, evidence, web, .gitignore for the new .db file | All tests, plus a new injection test for the new column | docs/architecture.md, docs/company-domains/design.md, README structure tree |
| Web API in web.py | web/index.html, test_web.py, any client that calls /api/kpis, /api/questions, /api/ask | test_web, test_unified | README endpoints section |
| A skill in skills/ | tools.py registry, unified_agent.py routing, any example question in that skill | test_unified, test_tools if present | skills/ README index, if added |
| A tool in tools.py | unified_agent.py, skills that call it, its parameter validation, its evidence fields | test_unified, test_tools | docs/tools.md if present, README tools list |
| .gitignore or a .db file | Never commit data/demo.db, data/company.db, experiments/*/spot.db, company.db, rejected.log, __pycache__, .venv | git status before every commit, git check-ignore for the .db file | Nothing in docs should quote a .db file as a deliverable; the seed script is the source of truth |

## 6. Symptom to file hints

- Answer is 0 when it should not be: check the period anchoring in agent.py
  and engine.py, the reference date is the last date in the demo data, not today.
- Answer abstains for a question you expect to work: check routing keywords
  in agent.py and unified_agent.py, then the registry measure and dimension,
  then the trial log for the abstention reason.
- A template passes locally but fails in the hardened validator: check
  SELECT *, UNION, a subquery, an unknown function, an unknown column, or an
  all-caps forbidden word. See section 3.
- A number changed after a seed change: do not edit the number in docs by
  hand. Re-run the seed, re-run the CLI demo, and copy the new number from
  tool output, with its period and definition.
- A test fails in test_web but passes in test_agent: check web.py, it wraps
  agent.ask, it does not implement its own routing. The bug is usually in
  the wrapper, the JSON shape, or the question list, not in the metric.
- A new employee question returns a salary or phone: stop. That column must
  not exist in the demo, or must not be in the allowlist. Remove it from the
  query, add a regression test, and check the audit log.
- Git status shows a .db file: stop the commit. Check .gitignore, check
  git check-ignore for that file, and remove the file from the index, never
  commit generated data.

## 7. Safe update and fix checklist

1. Read the impact row in section 5 for the file you are about to change.
2. Make the smallest change that fixes the issue, in code, not in a prompt.
3. If you add a table, column, metric, domain, tool, or skill, add it to
   the allowlist, the registry, the seed, and a test in the same change.
   A change without a test is not finished.
4. Run, in order: core tests, spot tests, company tests, hardened tests,
   unified tests. All must pass. A single passing suite is not enough.
5. Run the demo CLI and the unified CLI with at least one question per
   domain, one profit question, one warehouse question, one employee
   question, and one sensitive question. The sensitive question must abstain.
6. Try at least three injection questions by hand: a semicolon, a UNION,
   and a salary filter. All three must abstain, and the database must still
   answer a normal question afterwards.
7. Check git status. Only intended files, no .db, no __pycache__, no log,
   no venv. Check git diff for any number that changed without a reason.
8. Update docs and verified numbers from tool output, never by hand.
9. Commit with a message that names the change, the tests, and the review
   gate. Push only after step 4 to 8 are green, and only on Ahmed's explicit
   push instruction for that change.

Commands used in this repo, from the repo root:
PYTHONPATH=src python3 -m unittest discover -s tests
python3 -m unittest discover -s experiments/sql-db-spot/tests
python3 -m unittest discover -s experiments/company-domains/tests
python3 -m unittest discover -s experiments/security-hardened/tests
python3 -m unittest discover -s tests/test_unified.py 2>/dev/null || true
python3 scripts/seed_demo.py
python3 experiments/company-domains/seed_company.py

## 8. Migration plan, hardened validator to core

Do not swap the core validator in one step. The hardened validator rejects
shapes the core currently allows, and the core reference_date uses UNION
internally, which the hardened validator forbids for user-facing templates.

Step 1, done: hardened validator in experiments, with tests, audit log, and
this guide. Core, spot, company, and evidence templates are checked in tests.
Step 2, next: route all new tools and skills through the hardened validator
in the unified agent, while the core agent keeps its validator for its
existing 11 metrics, so no existing answer changes.
Step 3, review gate: Ahmed approves the migration, then the core validator is
replaced, reference_date is moved out of the user-facing path, and all tests
are re-run. If any core test fails, the migration stops and the old validator
stays.

## 9. What never to do

- Never interpolate user text, a question, a branch name, a part name, or an
  employee name into SQL by string formatting. Use a fixed registry value
  and a bound parameter.
- Never add a table or column to an allowlist because a question asked for it.
  Add it because a governed definition, a seed, and a test exist for it.
- Never use SELECT *, never return a whole row, never return a whole table.
- Never trust a model, a question list, or an external dataset to write SQL.
  The model explains, the database calculates, the template is in code.
- Never commit a .db file, a log file, a password, a token, or a personal
  phone or national ID, even in a test fixture. Use synthetic generic
  identifiers in the demo.
- Never present a demo profit, a demo revenue, or a demo warehouse value as
  a real Vo Technology number. Every demo answer must say demo, synthetic,
  and, for profit, that car purchase cost is not included.
- Never merge or push on a green single suite. All suites, the CLI demo,
  and the injection checks in section 7 must be green first.
