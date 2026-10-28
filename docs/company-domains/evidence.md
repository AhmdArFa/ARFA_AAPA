# Evidence Answers: Profit, Warehouse, Specific Employee

Status: EXPERIMENTAL, local only, NOT merged into core, NOT pushed.
Files: experiments/company-domains/evidence_engine.py, seed_company.py (extended).

## Profit, with evidence, not a single number

Formula, demo only:
Profit = invoiced revenue (sales + parts_sales + service labor for invoiced/closed cards)
         minus recorded costs in accounting_costs, by category.
Evidence in every answer: revenue by source with row counts, costs by category
with row counts, profit, margin, period, branch, source tables, and a caveat:
car purchase cost is NOT in the demo costs, so this is NOT net profit.
Real net profit requires real accounting COGS, connected and governed later.

## Warehouse, with evidence

Parts inventory: total stock quantity, low-stock rows (stock <= reorder_level),
inventory value = SUM(stock_qty * unit_price_egp), breakdown by part and branch.
Cars inventory: available cars count and value.
No part price is invented at query time: unit prices come from the seed price
list for the six demo parts, and are stored in parts_inventory.unit_price_egp.

## Specific employee, head-manager performance only

Demo employees are synthetic generic identifiers, for example "مندوب مبيعات 2"
and "فني صيانة 1", not real Vo Technology people.
Allowed answer fields: name, role, branch, and work performance linked by ID:
salesperson -> invoiced sales count and revenue; technician -> job cards total,
closed/invoiced count, labor sum; other roles -> existence, role, branch, and
a clear note that no direct work records exist for that role in the demo.
Forbidden, even for the head manager in this demo: salary, phone, national ID,
password, personal address. Those fields do not exist in the demo tables.
A separate governed, audited, head-manager-only metric would be needed before
any such field is ever shown, and Ahmed has not approved that.

## What is still abstained

Salary and phone questions, unknown domains, and any question that cannot be
mapped to profit, warehouse, or a named demo employee, with a stated reason.
