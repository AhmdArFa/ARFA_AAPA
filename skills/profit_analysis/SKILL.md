# Skill: Profit Analysis

Use when: the manager asks about company profit or earnings.
Formula, demo only: profit = invoiced revenue (sales + parts + service) minus recorded demo costs by category.
Always show: revenue by source with row counts, costs by category, profit, margin, period, branch, sources.
Always show the caveat: car purchase cost is NOT in demo costs, so demo profit is NOT net profit.
Forbidden: presenting demo profit as real Vo Technology net profit, estimating COGS, adding a cost category without a seed and a test.

Example: "ما هي أرباح الشركة في كل فترة الداتا التجريبية؟" -> revenue 119,202,530 EGP, costs 5,768,426 EGP, profit 113,434,104 EGP, margin 95.16 percent, with the caveat in the same answer.
Output shape: profit, revenue by source with row counts, costs by category, margin, period, branch, sources, caveat.
Common mistake: calling the result net profit, or estimating car purchase cost.
