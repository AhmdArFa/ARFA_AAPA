# Skill: Security Guard

Use always, before any database execution.
Steps: route to a registered tool, build SQL only from the registry, validate the whole template with the hardened validator, execute read-only with bound parameters, cap breakdown rows at 100, audit rejected templates.
Forbidden: SELECT *, UNION, subqueries, comments, unknown tables or columns, unknown functions, all-caps bypass, user text in SQL by string formatting, whole rows, salary or phone in any clause.
If validation fails, abstain, do not execute, do not show the database error.
See docs/SECURITY_AND_MAINTENANCE.md for the full rule list and the cross-file impact map.
