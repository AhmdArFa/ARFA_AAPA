# sql-db Spot: Architecture Pattern

Status: EXPERIMENTAL, local only, NOT merged into the core demo, NOT pushed.
Location: experiments/sql-db-spot/ (prototype code) and docs/sql-db-spot/ (this design).
Core demo location, unchanged: src/arfa_aapa/ (agent.py, metrics.py, security.py, web.py).

## Layered architecture, spot only

```
Question (Arabic or English, manager style)
  |
  v
[Presentation]  CLI / future web card, opt-in only, NOT the default demo UI
  |  calls ask() only
  v
[Application]   SqlDbSpot Facade
  |  normalise -> sensitive check -> route -> template -> validate -> execute -> format
  v
[Domain]        GovernedMetric Registry (8 curated strategies, fixed templates)
  |  parameters only: year, dealership name, no user SQL
  v
[Guard]         SpotValidator (whole-statement, SELECT only, allowlist tables/columns)
  |  rejects before any execution
  v
[Infrastructure] SqlDbRepository (SQLite, read-only, canonical schema)
  |  deterministic synthetic seed, seed 42, small and auditable
  v
[Data]          spot.db (generated locally, gitignored pattern, never committed
                in this experiment; the seed script is the source of truth)
```

## Why layered, and why separate from the core

- The core demo answers 11 governed 4S metrics from a synthetic 4S database
  (sales, service_job_cards, parts_sales, parts_inventory, surveys, branches).
- The sql-db spot answers 8 governed Sales + Service metrics from a different
  canonical schema (cars, dealerships, sales, service_records).
- Mixing the two schemas in one metrics.py would mix two definitions of
  revenue: core revenue is invoiced EGP, spot revenue is SUM(sellPrice) in the
  spot currency unit, with no invoice status in the source queries.
- Keeping the spot in experiments/ means the core tests, UI, and deck numbers
  cannot change by accident. A merge is a separate, reviewed decision.

## Data flow for one confirmed answer

1. User asks, for example: total sales revenue in 2022.
2. Facade normalises the question and routes it to total_sales_revenue.
3. The strategy supplies its fixed template:
   SELECT COALESCE(SUM(sale_price), 0) FROM sales
   WHERE strftime('%Y', sale_date) = :year
4. SpotValidator checks the whole template: SELECT only, one statement,
   table sales is allowed, no forbidden word anywhere.
5. Repository executes read-only, the database calculates, the Facade formats:
   value, unit, period (year), definition, source tables, confirmed = True.
6. If routing fails, or a sensitive word appears, or validation fails, the
   Facade returns an abstention with a missing reason, never a guessed number.

## Data flow for one rejected sql-db pair

Example: "Find the owner who registered the most cars."
1. Facade sensitive check sees owner-name intent.
2. No spot metric selects owner names, and owners is not in the allowlist.
3. Result: abstention, reason = owner names are excluded from this spot.
The original query is kept in curated.json only as audit provenance.

## Schema, canonical, spot only

- dealerships(dealership_id, name, state, year_established, num_employees)
- cars(serial_num, make, model, mpg, total_miles)
- sales(sale_id, serial_num, dealership_id, owner_ref, sale_price, sale_date,
       payment_method, financing_type)
  owner_ref is an anonymised integer, never a name.
- service_records(service_id, serial_num, service_center, service_type,
  service_cost, service_date, warranty_covered, service_manager_ref)
  service_manager_ref is an anonymised integer, never a name.

No parts table, no surveys table, no branches table in this spot, because
sql-db provides none of those. Claiming otherwise would be a false metric.

## Security and privacy boundaries

- Read-only SQLite connection, mode=ro, same as the core.
- No network, no Hugging Face call, no model call for calculation.
- No PII in seed data: no real names, phones, plates, salaries, or passwords.
  Makes and models are generic, dealership names are generic.
- Audit: the spot prototype logs the metric key and the abstention reason to
  stdout in the demo CLI only. A production version needs a persistent audit
  log before any real data is connected. That is a later phase, not this spot.

## What changes if a real dealership database arrives

Only three places change, in this order:
1. SqlDbRepository: connection and canonical mapping, behind the same interface.
2. GovernedMetric templates: only where the real definition differs, with a new
   definition text and a new test.
3. The allowlist: only after a security review, table by table, column by column.
Routing, validation order, Answer shape, and the abstain rule do not change.

## Open decisions, not assumed

- Currency: spot numbers are in the seed currency unit, labelled as such.
  They are NOT EGP and NOT core revenue, and must not be added to core totals.
- Periods: the spot uses calendar year (from sellDate / serviceDate), while the
  core uses last 30 / 90 days anchored to the last demo date. Do not mix periods.
- Owners: if a future manager legitimately needs an anonymised owner count,
  that is a new governed metric with its own definition and review, not a
  reopening of owner-name queries.
