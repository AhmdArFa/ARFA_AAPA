# Skill: Security Guard

Use always, before any database execution.
Steps: route to a registered tool, build SQL only from the registry, validate the whole template with the hardened validator, execute read-only with bound parameters, cap breakdown rows at 100, audit rejected templates.
Forbidden: SELECT *, UNION, subqueries, comments, unknown tables or columns, unknown functions, all-caps bypass, user text in SQL by string formatting, whole rows, salary or phone in any clause.
If validation fails, abstain, do not execute, do not show the database error.
See docs/SECURITY_AND_MAINTENANCE.md for the full rule list and the cross-file impact map.

Example rejected: "SELECT * FROM sales", "SELECT amount_egp FROM sales UNION SELECT amount_egp FROM parts_sales", a question containing a semicolon and DROP.
Output shape on rejection: abstention, never the database error, with a rejected template hash in the audit log.
Common mistake: editing the allowlist because a question asked for a column, without a definition, a seed, and a test.
