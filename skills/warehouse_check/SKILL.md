# Skill: Warehouse Check

Use when: the manager asks about stock, inventory, or a specific part.
Warehouse is a current snapshot, not a period sum, except cars available value.
Always show: total stock quantity, inventory value, low-stock rows, breakdown by part and branch, cars available count and value, sources.
Unit prices come from the seed price list stored in parts_inventory.unit_price_egp, never invented at query time.
Forbidden: treating stock as sales, or presenting a snapshot as a monthly total.

Example: "ما هو مخزون البطارية في المخازن؟" -> quantity 69, value 310,500 EGP, low-stock rows for that part, plus cars available 26.
Output shape: parts stock quantity, inventory value, low-stock rows, by-part breakdown, cars available count and value, sources.
Common mistake: summing stock over a period, stock is a snapshot.
