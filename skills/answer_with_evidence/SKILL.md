# Skill: Answer With Evidence

Use when: the manager asks any business question, in any company domain.
Steps:
1. Route the question to one registered tool, never to free SQL.
2. Let the database calculate, using a fixed template and bound parameters.
3. Return value, period, definition, source tables, and, for profit and warehouse, component breakdown.
4. If no tool matches, abstain and list available tools, never guess.
Forbidden: inventing a number, using a previous question as a manager question, returning a whole row, returning salary or phone.

Example: "إجمالي الإيراد في آخر 30 يوم" -> tool total_revenue -> value 18,352,310 EGP, period 2026-09-28 to 2026-10-27, definition and sources sales, parts_sales, service_job_cards.
Output shape: confirmed or abstain, text, value, definition, source tables, missing reason if abstain.
Common mistake: answering from a previous question, or adding two periods together.
