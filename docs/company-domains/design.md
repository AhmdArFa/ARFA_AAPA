# Company Domains: Domain-Agnostic Answering, Trial Mode

Status: EXPERIMENTAL, local only, NOT merged into core, NOT pushed.
User instruction 2026-10-28: answer based on company data for ANY domain the
manager asks about in the company, not only 4S, not only pre-defined metrics.
User instruction 2026-10-28 (trial): do NOT collect manager questions in advance.
The manager asks during the trial, based on the data in front of him.

## Core rule, unchanged

The database calculates, the agent only explains. No invented numbers, no free
SQL from the user, no PII, no salary, phone, customer name, or password in any
clause. If a domain, measure, or dimension is not registered, the answer is an
abstention that lists the available domains, never a guess.

## Shift: from exact metric routing to Domain Registry

Old core agent: question text must match a keyword for one of 11 fixed metrics.
That fails in a trial, because the manager will not use golden-question wording.

New engine: a Domain Registry. Each domain registers, in code, not in a prompt:
- table, date column, amount column (or none)
- allowed measures: COUNT, SUM, AVG, only over allowed numeric columns
- allowed dimensions: branch, month, type, model, status, source, only
- a written definition for each measure, in Arabic
- forbidden columns, always: names, phones, salaries, passwords, national IDs

A question is answered only if it maps to: one domain + one measure + at most
one dimension + a period + optionally a branch. Everything else abstains.

## Domains in the demo

From the Vo Technology ERP modules, not invented:
- sales: sales table, invoiced revenue only for SUM, COUNT of invoiced rows
- service: service_job_cards, labor SUM, COUNT by status or service_type
- parts: parts_sales, amount SUM, COUNT by part_name
- survey: surveys, AVG score, COUNT by branch or month
- crm: crm_leads, COUNT by source or status, no lead names
- accounting: accounting_invoices, SUM of paid invoices, COUNT of overdue invoices
- cars: cars_inventory, COUNT by status or model, SUM of available car prices

Parts, surveys, and the three new domains are demo data only, seed 42,
clearly synthetic, no real Vo Technology data, no PII. The new tables are added
in the experiment database only, never in the core demo.db.

## Answer shape, for any domain

domain, measure, dimension (or none), period, value or breakdown rows,
definition, source tables, confirmed or abstention with missing reason.
Example definition, generated from the registry, not from the model:
"مجموع مبالغ الفواتير المدفوعة، حسب الفرع، في آخر 30 يوم. المصدر: accounting_invoices."

## What this engine will NOT do

- It will not answer HR, salary, or personal data questions, even if the manager
  asks. Those domains are not registered, and the words themselves abstain.
- It will not join two domains in one answer in this prototype, for example
  sales joined to CRM leads, unless that join is registered and tested later.
- It will not use the Hugging Face sql-db queries, golden questions, or any
  previous question list as a manager question list. Those remain test material only.
- It will not connect to real Vo Technology data. A real connection is a later,
  reviewed phase, with role scope: the head manager sees company domains,
  other users see only their own module, per the standing Vo boundary.

## Trial feedback loop, after the trial, not before

Unanswered questions are logged locally in the experiment only, with the
question text and the abstention reason, never with personal data.
After the trial, Ahmed reviews the log and decides, one by one, which
unanswered patterns deserve a new registered domain, measure, or dimension.
Logging does not auto-add a metric.
