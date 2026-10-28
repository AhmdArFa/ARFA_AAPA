# Skill: Employee Performance, Head Manager Only

Use when: the manager asks about a specific employee by exact demo name.
Allowed: name, role, branch, and work performance linked by ID, salesperson invoiced sales, technician job cards and labor.
Forbidden, even for the head manager in the demo: salary, phone, national ID, password, personal address. Those fields do not exist in the demo tables.
If the employee name is not in the demo list, abstain, do not guess a similar name.
Other roles: show existence, role, and branch, and a clear note that no direct work records exist for that role in the demo.

Example: "كم كارت صيانة قفل فني صيانة 1؟" -> technician, Giza, 105 job cards, 57 closed or invoiced, labor 688,997 EGP.
Output shape: name, role, branch, work counts and totals, sources.
Common mistake: adding salary, phone, or a personal field, or guessing a similar employee name.
