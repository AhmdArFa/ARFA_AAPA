# ARFA AAPA

Business Q&A assistant for the head manager, demo edition.

## 1. Idea in one paragraph

A head manager needs business insights fast. Today, asking the data analysis team for a report can take a day or more, so decisions are delayed or made on feeling instead of data. ARFA AAPA answers the manager in Arabic, immediately, from business data, with the number, its period, its exact definition, and its source. If the evidence is not enough, it abstains instead of guessing.

Golden rule of this project: not knowing is better than giving a wrong answer, because the answer will drive a decision.

## 2. Data provenance, read this first

This repository is a demo only, and it is important to state exactly what it is and what it is not:

- The dataset is synthetic and external to any real company. It was generated locally to test the project. It is not real Vo Technology data, and it contains no real customers, employees, salaries, phone numbers, or other personal data.
- The test questions in `evals/golden_questions.json` are demo questions written to test the project. No question data has been collected from any head manager, and no manager interview, real question list, or real company metric has been used in this demo.
- The metric definitions in this README are demo definitions. They have not been approved by a head manager or by Vo Technology.
- Vo Technology (4S PLUS: Sales, Spare Parts, Service, Survey) is the agreed pilot company for a later phase only. It is not a data source in this demo.

Collecting real head manager questions and agreeing real metric definitions is a separate later phase, listed under Review gates and roadmap below. Until that phase happens, nothing in this demo should be presented as a real company result.

## 3. Who this is for, and who it is not for yet

Target user, first phase only: the head manager.

Not in scope yet:

- Other managers, employees, or multiple roles.
- Multiple companies or multiple tenants.
- Write, update, or delete actions on any business system.
- A general day manager assistant, scheduling, email, or chat assistant.
- Any production deployment, login system, or connection to a real company database.

Scale is a later decision, not a current feature.

## 4. Current status

- Repository: standalone, built from scratch. It has no code dependency on the older AI-Personal-Assistant-Agent platform repository. Design lessons from that platform were reused as ideas only.
- Unified agent v3, 2026-10-28, after all tests green: unified agent in src/arfa_aapa/unified_agent.py, tools registry in tools.py, skills in skills/, hardened validator as the core validator in src/arfa_aapa/security.py (canonical implementation in src/arfa_aapa/hardened.py), company domains and evidence engines in src/arfa_aapa/domains.py and evidence.py, web UI in src/arfa_aapa/web.py now uses the UnifiedAgent, CI in .github/workflows/ci.yml, security and maintenance guide in docs/SECURITY_AND_MAINTENANCE.md. Canonical source rule: src/ is canonical, experiments/ files are thin wrappers over src/, never edited for rules or templates. Earlier pushed versions were GitHub main, commit 5fc45a3, then c82b63d.
- Demo presentation: an 8 slide deck was delivered separately. It is not inside this repository.
- Tests: 62 in total pass, core 30, sql-db spot 10, company domains 19, hardened 3, see Testing and evaluation.
- Real data connection: none.
- Production use: not ready.

## 5. How it works

The flow is deliberately boring, because boring is trustworthy:

1. The manager asks a question in Arabic, in the CLI or in the local web UI. The web UI now uses the UnifiedAgent, so it can answer profit, warehouse, CRM, and employee questions, not only the 11 core metrics.
2. The UnifiedAgent in `src/arfa_aapa/unified_agent.py` routes the question to exactly one registered tool in `tools.py`, in order: sensitive and injection guards, then evidence tools (profit, warehouse, employee), then the core agent, then company domains. It never invents a new metric, and it never writes free SQL from the user question.
3. The tool builds a fixed SQL template with parameters only: branch and period.
4. The validator in `src/arfa_aapa/security.py`, canonical implementation in `src/arfa_aapa/hardened.py`, checks the whole statement before execution: SELECT only, one statement only, allowed tables and allowed columns only, allowed functions only, and no forbidden word anywhere in the statement, including WHERE, JOIN, ORDER BY, and GROUP BY, case-insensitive, with no SELECT *, no UNION, and no subqueries.
5. The database calculates the number. The model, or in this demo the agent code, only explains the result. It does not calculate.
6. The answer returns in a fixed shape: value, period, definition, source tables, and a confirmed or abstained status.
7. If no metric matches, if the question asks for sensitive data, or if there is not enough data, the answer is an explicit abstention with the reason and what is missing.

## 6. Demo dataset

Generated by `scripts/seed_demo.py` and `src/arfa_aapa/data/seed.py`, with a fixed random seed of 42, so the demo is reproducible. The database file `data/demo.db` is generated locally and is excluded from Git by `.gitignore`.

Counts:

- Branches: 3, New Cairo, Giza, Alexandria.
- Car sales: 180 rows.
- Service job cards: 420 rows.
- Parts sales: 600 rows.
- Parts inventory: 18 rows, 6 parts in 3 branches.
- Surveys: 300 rows.
- Date range: 2026-01-01 to 2026-10-27.

Tables:

- `branches(id, name, city)`
- `sales(id, branch_id, sale_date, vehicle_model, amount_egp, status, salesperson_id)`
- `service_job_cards(id, branch_id, opened_date, closed_date, status, service_type, labor_amount_egp, sold_hours, actual_hours, technician_id)`
- `parts_sales(id, branch_id, sale_date, part_name, quantity, amount_egp)`
- `parts_inventory(id, branch_id, part_name, stock_qty, reorder_level, unit_price_egp)`
- `surveys(id, branch_id, survey_date, score_1_5)`
- Company demo tables, built by `scripts/seed_company.py` into `data/company.db`, gitignored: `crm_leads(id, branch_id, created_date, source, status)`, `accounting_invoices(id, branch_id, invoice_date, amount_egp, status)`, `accounting_costs(id, branch_id, cost_date, category, amount_egp)`, `cars_inventory(id, branch_id, vehicle_model, status, price_egp)`, `employees(id, name, role, branch_id)` with no salary, phone, national ID, or password column.

Money is in EGP. Only invoiced sales count as sales revenue. Only invoiced or closed job cards count as service revenue. Cancelled sales are excluded.

Reference date: periods are anchored to the last date present in the demo data, 2026-10-27, not to the current system date, so results are reproducible.

## 7. Governed metrics

There are 11 metrics. Each one has one written definition and one fixed SQL template. The agent cannot invent a new one.

| Metric key | Metric | Definition | Source tables | Unit |
|---|---|---|---|---|
| `total_revenue` | Total revenue | Invoiced car sales plus parts sales plus labor for invoiced or closed job cards, in the period. | sales, parts_sales, service_job_cards | EGP |
| `sales_revenue` | Car sales revenue | Invoiced car sales only, cancelled sales excluded. | sales | EGP |
| `service_revenue` | Service revenue | Labor for invoiced or closed job cards only. | service_job_cards | EGP |
| `parts_revenue` | Parts revenue | Parts sales in the period. | parts_sales | EGP |
| `open_job_cards` | Open job cards | Job cards with status open or ready for invoicing, up to the end of the period. | service_job_cards | cards |
| `overdue_job_cards` | Overdue job cards | Open or ready job cards opened more than 14 days before the end of the period. | service_job_cards | cards |
| `average_satisfaction` | Average customer satisfaction | Average survey score from 1 to 5 in the period. | surveys | out of 5 |
| `service_hours_efficiency` | Service hours efficiency | Actual hours divided by sold hours, times 100, for invoiced or closed job cards. Above 100 means more actual time than sold time. | service_job_cards | percent |
| `top_selling_part` | Top selling part | The part with the highest parts revenue in the period. | parts_sales | EGP, with part name |
| `low_stock_parts` | Parts below reorder level | Inventory items whose stock is at or below the reorder level, current snapshot. | parts_inventory | items |
| `best_branch` | Best branch, car sales | The branch with the highest invoiced car sales revenue in the period. | branches, sales | EGP, with branch name |

## 8. Periods and branch filtering

Default period: last 30 days, anchored to the demo reference date.

Supported periods in a question:

- Last 30 days: default.
- Last 90 days.
- Current month: from the first day of the reference month to the reference date.
- Last month: the previous calendar month.
- All demo data: 2026-01-01 to the reference date.

Branch filtering: if the question names New Cairo, Giza, or Alexandria, the metric is filtered to that branch. The best branch metric is an exception: it compares branches and is not filtered by a branch name in the question.

## 9. Answer contract

Every answer, in the CLI, in the web UI, and in the API, uses the same fields:

- `question`: the original question.
- `metric_key`: one of the 11 metric keys, or null for an abstention.
- `metric_name`: the human readable metric name, or empty for an abstention.
- `text`: the full Arabic answer text, including value, period, definition, and sources.
- `confirmed`: true for a database backed answer, false for an abstention.
- `period_label`: for example, last 30 days.
- `definition`: the governed definition of the metric.
- `source_tables`: the tables the number came from.
- `missing`: the reason for an abstention, or empty for a confirmed answer.
- `value`: the number, part name, or branch name, or null for an abstention.
- `unit`: EGP, cards, percent, out of 5, or similar.
- `detail`: extra evidence, for example revenue for a top part, or sold and actual hours.

Abstention examples, both tested:

- Salary questions: abstained, because salaries are sensitive and outside the governed metrics.
- Market forecasts for next year: abstained, because no metric covers them and the demo has no forecast data.

An abstention is a correct result in this project, not a failure. It must never be counted as a confirmed answer.

## 10. Project structure

```
ARFA_AAPA/
  README.md
  pyproject.toml
  .gitignore
  docs/
    architecture.md
    charter.md
    metrics.md
    gates/
      demo-endpoint-review.md
      ui-endpoint-review.md
  evals/
    golden_questions.json
  scripts/
    seed_demo.py
  src/
    arfa_aapa/
      __init__.py
      __main__.py
      agent.py
      cli.py
      metrics.py
      security.py
      web.py
      data/
        __init__.py
        database.py
        seed.py
  tests/
    test_agent.py
    test_metrics.py
    test_security.py
    test_web.py
  web/
    index.html
  data/
    demo.db (generated locally, not in Git)
```

## 11. Coding details

### Stack and clean code rules

- Language: Python, version 3.11 or later.
- Package: `arfa-aapa`, version 0.1.0, src layout, defined in `pyproject.toml`.
- Dependencies: none. Only the Python standard library is used, including `sqlite3` and `http.server`. This is intentional: the demo should run without installing packages and without an external model service.
- No external model calculates numbers. The database calculates, the code explains.
- The data layer is isolated in `src/arfa_aapa/data/`, so a named external dataset can replace the synthetic generator later without changing the agent routing or the security layer.
- No credentials, no API keys, and no personal data are stored in this repository.

### Modules

- `src/arfa_aapa/security.py`: `validate_sql()`, allowed tables, forbidden words, whole statement validation. See Security and privacy.
- `src/arfa_aapa/metrics.py`: the 11 governed metrics, each as one function with one fixed SQL template and one definition. `METRICS` maps a metric key to its function.
- `src/arfa_aapa/agent.py`: Arabic normalization, period parsing, branch detection, metric routing, the `Answer` dataclass, and the abstention rules. Routing is most specific first, so a specific question such as top selling part is not swallowed by a general revenue question.
- `src/arfa_aapa/data/database.py`: read-only SQLite connection using `mode=ro`, and `reference_date()`, which returns the last date present in the demo data.
- `src/arfa_aapa/data/seed.py`: deterministic synthetic data generation, seed 42.
- `src/arfa_aapa/cli.py`: single question mode, golden demo mode, and interactive mode.
- `src/arfa_aapa/web.py`: local web server and API handlers, see HTTP endpoints.
- `web/index.html`: Arabic, right to left UI. KPI cards, suggested questions, and a confirmed or abstain answer card. No external assets.

### How to add a new metric, correctly

1. Add one function in `src/arfa_aapa/metrics.py` with one definition and one fixed SQL template, using allowed tables only.
2. Add the metric key to `METRICS`.
3. Add its definition to `docs/metrics.md` and to the table in this README.
4. Add routing for it in `src/arfa_aapa/agent.py`, most specific first.
5. Add at least one golden question in `evals/golden_questions.json` and one test in `tests/`.
6. Never guess a definition, and never add a metric because a single demo question needs it without writing its definition first.

## 12. Quick start

Prerequisites: Python 3.11 or later. No package installation is required.

```bash
git clone https://github.com/AhmdArFa/ARFA_AAPA.git
cd ARFA_AAPA
python3 scripts/seed_demo.py
```

Run all golden demo questions:

```bash
PYTHONPATH=src python3 -m arfa_aapa.cli --demo
```

Ask one question:

```bash
PYTHONPATH=src python3 -m arfa_aapa.cli "ايه ايراد الصيانة اخر 30 يوم؟"
```

Interactive mode, no arguments, type a question, type `خروج`, `exit`, or `quit` to stop:

```bash
PYTHONPATH=src python3 -m arfa_aapa.cli
```

Run the local web UI:

```bash
PYTHONPATH=src python3 -m arfa_aapa.web --port 8000
```

Then open `http://127.0.0.1:8000` in a browser. The server binds to 127.0.0.1 only. It is not a public link and it is not a production deployment.

Run the tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

## 13. HTTP endpoints

Base URL for the local demo server: `http://127.0.0.1:8000`. All JSON responses use UTF-8.

### Web pages

| Method and path | Description | Response |
|---|---|---|
| `GET /` | Manager demo UI, Arabic, right to left. | HTML page, `web/index.html` |
| `GET /index.html` | Same UI page. | HTML page |

### API endpoints

| Method and path | Description | Request | Success response |
|---|---|---|---|
| `GET /api/health` | Server and demo status check. | None. | `{"status": "ok", "demo": true, "read_only": true}` |
| `GET /api/kpis` | The 4 KPI cards shown on the UI: total revenue, service revenue, open job cards, average satisfaction, all for the last 30 days. | None. | JSON array of 4 answer objects, see Answer contract. |
| `GET /api/questions` | Suggested questions for the UI. Only golden questions with a confirmed metric are included, 11 questions. Abstention test questions are excluded. | None. | JSON array of strings, in Arabic. |
| `POST /api/ask` | Ask one business question. | JSON body: `{"question": "..."}`. The question must be a non empty string. | One answer object, see Answer contract. `confirmed` is false for an abstention. |

Example request:

```bash
curl -X POST http://127.0.0.1:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "ايه اجمالي الايراد اخر 30 يوم؟"}'
```

Example response, verified demo numbers:

```json
{
  "question": "ايه اجمالي الايراد اخر 30 يوم؟",
  "metric_key": "total_revenue",
  "metric_name": "إجمالي الإيراد",
  "text": "إجمالي الإيراد في آخر 30 يوم (2026-09-28 إلى 2026-10-27): 18352310.0 جنيه. التعريف: مجموع المبيعات المفوترة زائد قطع الغيار زائد أجور الصيانة للكروت المفوترة أو المغلقة، في الفترة المحددة. المصدر: sales, parts_sales, service_job_cards.",
  "confirmed": true,
  "period_label": "آخر 30 يوم",
  "definition": "مجموع المبيعات المفوترة زائد قطع الغيار زائد أجور الصيانة للكروت المفوترة أو المغلقة، في الفترة المحددة.",
  "source_tables": ["sales", "parts_sales", "service_job_cards"],
  "missing": "",
  "value": 18352310.0,
  "unit": "جنيه",
  "detail": ""
}
```

Example abstention response:

```bash
curl -X POST http://127.0.0.1:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "ايه مرتبات الموظفين؟"}'
```

The response has `confirmed: false`, `metric_key: null`, and `missing` explaining that the question asks for sensitive data outside the governed metrics.

Error responses:

- `400`, invalid JSON: `{"error": "invalid JSON"}`.
- `400`, empty question: `{"error": "question is required"}`.
- `404`, unknown path: `{"error": "not found"}`.
- `500`, server error, for example the demo database is missing: `{"error": "..."}`. Run `python3 scripts/seed_demo.py` first.

### CLI endpoints

These are the command line entry points, not HTTP endpoints, but they use the same agent and answer contract:

- `python3 scripts/seed_demo.py`: rebuilds `data/demo.db`, force rebuild.
- `PYTHONPATH=src python3 -m arfa_aapa.cli --demo`: runs all golden questions.
- `PYTHONPATH=src python3 -m arfa_aapa.cli "question"`: asks one question.
- `PYTHONPATH=src python3 -m arfa_aapa.cli`: interactive mode.
- `PYTHONPATH=src python3 -m arfa_aapa.web --port 8000`: starts the local web UI and API.

## 14. Testing and evaluation, verified results

Test files:

- `tests/test_security.py`: 5 tests. Allows a clean SELECT, rejects a write, rejects an unknown table, rejects a forbidden column in WHERE even when the SELECT list is clean, and rejects stacked statements.
- `tests/test_metrics.py`: 1 test. Service revenue is positive and total revenue covers service revenue over the full demo period.
- `tests/test_agent.py`: 3 test methods, including a subtest for every golden question. Checks routing, confirmed answers with source and definition, and abstention for a sensitive question with no metric key.
- `tests/test_web.py`: 7 tests. Health, confirmed ask, abstaining ask, 4 KPI answers, plus unified web profit, warehouse, and unified suggested questions.
- `tests/test_unified.py`: 14 tests. Core, CRM, profit with evidence and caveat, warehouse, employee, salary abstention, injection abstention with database survival, out-of-scope abstention, tools registry, skills files, hardened all-caps block, and canonical source checks.
- Experiments: sql-db spot 10, company domains 19, hardened 3.

Total: 62 tests, 62 pass. CI in .github/workflows/ci.yml runs all suites on Python 3.11 and 3.12, after building demo, company, and spot databases.

Golden questions, `evals/golden_questions.json`: 13 questions. 11 confirmed, 2 abstentions. The 2 abstentions are a salary question and a market forecast question. Both are correct abstentions, not failures.

Verified demo results, from the CLI demo run:

| Demo question, period | Result |
|---|---|
| Total revenue, last 30 days, 2026-09-28 to 2026-10-27 | 18,352,310 EGP |
| Car sales revenue, last month, 2026-09-01 to 2026-09-30 | 8,462,692 EGP |
| Service revenue, last 30 days | 132,915 EGP |
| Parts revenue, last 90 days, 2026-07-30 to 2026-10-27 | 1,055,700 EGP |
| Open job cards | 192 cards |
| Overdue job cards | 181 cards |
| Average customer satisfaction, last 30 days | 4.19 out of 5 |
| Service hours efficiency, last 30 days | 99.3 percent, sold 96.5 hours, actual 95.8 hours |
| Top selling part, last 30 days | Battery, revenue 135,000 EGP |
| Parts below reorder level, current snapshot | 4 items |
| Best branch, car sales, last 30 days | Alexandria, revenue 8,961,878 EGP |

All numbers above are synthetic demo numbers. They are not Vo Technology results.

## 15. Security and privacy

- Read-only first: the database connection uses SQLite read-only mode, and the validator allows SELECT only.
- Allowed tables and columns only: core `branches`, `sales`, `service_job_cards`, `parts_sales`, `parts_inventory`, `surveys`, plus company `crm_leads`, `accounting_invoices`, `accounting_costs`, `cars_inventory`, `employees` (id, name, role, branch_id only), plus spot tables in experiments. Allowed functions only, no SELECT *, no UNION, no subqueries, case-insensitive forbidden words.
- Rejected templates are audited: `src/arfa_aapa/hardened.py` writes rejected template hashes and reasons to `rejected.log`, gitignored, never with a password or personal value.
- Whole statement validation: a forbidden word or an unknown table anywhere in the statement is rejected, not only in the SELECT list. This was a deliberate design lesson: checking only the SELECT list would let an unlisted column leak through WHERE, ORDER BY, GROUP BY, or JOIN.
- Forbidden words include write operations such as insert, update, delete, drop, alter, create, and truncate, and sensitive columns such as password, salary, phone, customer name, and national ID. The demo schema does not contain these columns at all.
- No free SQL from the user: the user question never becomes SQL directly. It routes to a fixed template.
- No personal data in the demo: no customer names, no phones, no salaries, no national IDs.
- Local only: the web server binds to 127.0.0.1 only.
- No training: demo data is not used to train any model, and no external model service is called for calculations in this demo.

Demo limitations, stated plainly:

- No login, no roles, and no multi-user access control. Do not expose this demo server to a network and do not connect it to real data in its current form.
- Audit log covers rejected templates only, not a full persistent answer audit log. Answers are not stored in this demo, except the in-memory trial log.
- No input authentication on the local API. Local only is the only protection in this demo.

## 16. Review gates and roadmap

This project works step by step, with a review endpoint after each point. No phase starts without an explicit review decision.

| Gate or phase | Deliverable | Review question | Status |
|---|---|---|---|
| Gate 0, scope | Standalone repo, head manager only first, pilot company Vo Technology for a later phase. | Is the scope correct? | Decided, repo standalone, pilot Vo Technology. Charter text itself still awaits a final explicit approval, even though the push below was explicitly authorized. |
| Demo endpoint | Synthetic 4S dataset, 11 metrics, CLI demo, golden questions, tests. | Is the design and demo acceptable? | Built, tested, pushed. |
| UI endpoint | Local Arabic RTL UI, 4 KPI cards, suggested questions, confirmed or abstain answer card, HTTP API. | Is the UI acceptable as a first manager trial? | Built, tested, pushed. |
| Deck endpoint | 8 slide demo presentation, delivered separately, not inside this repo. | Is the deck acceptable? | Delivered, review pending. |
| Next endpoint, verification | Fresh clone from GitHub, seed, tests, and UI run, to prove the pushed version works on its own. | Does the pushed version work standalone? | Recommended next step, not started yet. |
| Phase 1, real questions | Real head manager questions, mapped to 4S modules and to agreed metrics, added as golden questions. No manager question data has been collected yet. | Which questions does the manager really ask, and what does each metric mean? | Not started. This must happen before real data work. |
| Phase 2, security and real data | Read-only real data access, allowlist, roles, audit log, deployment decision, security review. | Is real data access safe and approved? | Not started. |
| Phase 3, hardening | Persistent audit log, periodic evaluation, fallback to the data analysis team on abstention, monitoring for errors and leakage. | Is it ready for limited daily use? | Not started. |
| Phase 4, scale decision | Only after a successful pilot: other managers, other companies, new sources, new roles, each as its own phase with its own review. | Should we scale, and to what, exactly? | Not started, and not approved. |

## 17. Troubleshooting

- Database not found: run `python3 scripts/seed_demo.py` first, and `python3 scripts/seed_company.py` for company domains, profit, warehouse, and employee questions. The web server fails fast with a clear message if the database is missing.
- Tests fail with a missing database: the test suite builds its own temporary database, so it does not depend on `data/demo.db`. The web tests use the default demo database, so seed it first if you run only the web tests after a clean clone.
- Port already in use: start the web server with a different port, for example `PYTHONPATH=src python3 -m arfa_aapa.web --port 8765`, then open `http://127.0.0.1:8765`.
- A question abstains: check the `missing` field. It means no governed metric matches, the question is sensitive, or there is not enough demo data in the period. Do not treat an abstention as a bug unless the question should match a documented metric, in which case add routing, a definition, a golden question, and a test, in that order.

## 18. What this demo is not

- It is not a Vo Technology product, and it is not connected to Vo Technology.
- It is not a production system, and it has no login, roles, audit log, or network protection.
- It is not a general AI assistant, and it does not answer questions outside its registered tools, 11 core metrics, 7 company domains, and evidence tools.
- It does not predict the future, and it does not answer salary, personal, or market forecast questions.
- Its numbers are synthetic test numbers, and they must never be quoted as real company results.
