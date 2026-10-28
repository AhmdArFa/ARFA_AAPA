"""Build experiments/company-domains/company.db: core 4S demo + 3 new demo domains.
Stdlib only. Core demo is built by importing the core seed (seed 42), then new
tables are added here. No real Vo data, no PII, no names, phones, or salaries.
Run from repo root: python3 scripts/seed_company.py, creates data/company.db (gitignored)
"""
import random, sqlite3, sys
from datetime import date, timedelta
from pathlib import Path
HERE = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
from arfa_aapa.data.seed import build_demo_db

def main():
    db = REPO_ROOT / "data" / "company.db"
    build_demo_db(db, force=True)
    rng = random.Random(42)
    start, end = date(2026, 1, 1), date(2026, 10, 27)
    def rand_date():
        return (start + timedelta(days=rng.randint(0, (end - start).days))).isoformat()
    con = sqlite3.connect(db)
    con.executescript("""
    CREATE TABLE crm_leads (id INTEGER PRIMARY KEY, branch_id INTEGER NOT NULL, created_date TEXT NOT NULL, source TEXT NOT NULL, status TEXT NOT NULL);
    CREATE TABLE accounting_invoices (id INTEGER PRIMARY KEY, branch_id INTEGER NOT NULL, invoice_date TEXT NOT NULL, amount_egp REAL NOT NULL, status TEXT NOT NULL);
    CREATE TABLE cars_inventory (id INTEGER PRIMARY KEY, branch_id INTEGER NOT NULL, vehicle_model TEXT NOT NULL, status TEXT NOT NULL, price_egp REAL NOT NULL);
    """)
    sources = ["website", "showroom", "phone", "referral"]
    lead_status = ["new", "contacted", "won", "lost"]
    for i in range(1, 121):
        con.execute("INSERT INTO crm_leads VALUES (?,?,?,?,?)",
                    (i, rng.choice([1, 2, 3]), rand_date(), rng.choice(sources), rng.choice(lead_status)))
    inv_status = ["paid", "paid", "paid", "paid", "paid", "paid", "paid", "unpaid", "unpaid", "overdue"]
    for i in range(1, 151):
        con.execute("INSERT INTO accounting_invoices VALUES (?,?,?,?,?)",
                    (i, rng.choice([1, 2, 3]), rand_date(), rng.randint(5000, 90000), rng.choice(inv_status)))
    models = ["Sedan A", "SUV B", "Hatchback C", "Pickup D"]
    car_status = ["available", "available", "sold", "sold", "reserved"]
    for i in range(1, 61):
        con.execute("INSERT INTO cars_inventory VALUES (?,?,?,?,?)",
                    (i, rng.choice([1, 2, 3]), rng.choice(models), rng.choice(car_status), rng.randint(350000, 1200000)))
    # --- Evidence extension: costs, employees, warehouse unit prices ---
    con.executescript("""
    CREATE TABLE accounting_costs (id INTEGER PRIMARY KEY, branch_id INTEGER NOT NULL, cost_date TEXT NOT NULL, category TEXT NOT NULL, amount_egp REAL NOT NULL);
    CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL, branch_id INTEGER NOT NULL);
    ALTER TABLE sales ADD COLUMN salesperson_id INTEGER;
    ALTER TABLE service_job_cards ADD COLUMN technician_id INTEGER;
    ALTER TABLE parts_inventory ADD COLUMN unit_price_egp REAL;
    """)
    categories = ["parts_purchase", "service_cost", "operating", "marketing"]
    for i in range(1, 201):
        con.execute("INSERT INTO accounting_costs VALUES (?,?,?,?,?)",
                    (i, rng.choice([1, 2, 3]), rand_date(), rng.choice(categories), rng.randint(2000, 60000)))
    employees = []
    for i in range(1, 5):
        employees.append((i, f"مندوب مبيعات {i}", "salesperson", (i % 3) + 1))
    for i in range(1, 5):
        employees.append((4 + i, f"فني صيانة {i}", "technician", (i % 3) + 1))
    employees.append((9, "مستشار خدمة 1", "service_advisor", 1))
    employees.append((10, "مستشار خدمة 2", "service_advisor", 2))
    employees.append((11, "محاسب 1", "accountant", 1))
    employees.append((12, "مسؤول قطع غيار 1", "parts_officer", 3))
    con.executemany("INSERT INTO employees VALUES (?,?,?,?)", employees)
    # Assign work deterministically by row id, so tests can recompute it
    for row_id, in con.execute("SELECT id FROM sales ORDER BY id"):
        con.execute("UPDATE sales SET salesperson_id = ? WHERE id = ?", (1 + (row_id - 1) % 4, row_id))
    for row_id, in con.execute("SELECT id FROM service_job_cards ORDER BY id"):
        con.execute("UPDATE service_job_cards SET technician_id = ? WHERE id = ?", (5 + (row_id - 1) % 4, row_id))
    prices = {"فلتر زيت": 350, "تيل فرامل": 1200, "بطارية": 4500, "إطار": 2800, "بوجيهات": 600, "مساعدين": 3200}
    for part, price in prices.items():
        con.execute("UPDATE parts_inventory SET unit_price_egp = ? WHERE part_name = ?", (price, part))
    con.commit()
    print("company.db built: core 4S + crm_leads=120 accounting_invoices=150 cars_inventory=60 costs=200 employees=12")
    con.close()
if __name__ == "__main__":
    main()
