"""Deterministic synthetic seed for the sql-db spot. Stdlib only, seed 42.
No real names, phones, plates, salaries, or passwords. Generic makes only.
Run from experiments/sql-db-spot: python3 seed.py
Creates spot.db in the same directory.
"""
import random, sqlite3
from pathlib import Path
HERE = Path(__file__).resolve().parent
random.seed(42)
MAKES = [("toyota", "corolla"), ("toyota", "camry"), ("ford", "focus"), ("bmw", "320i"), ("skoda", "octavia")]
DEALERS = [(1, "City Auto Dealership", "CA", 2010, 40), (2, "Auto World Dealership", "NY", 2012, 55), (3, "North Auto Dealership", "TX", 2015, 30)]
def main():
    db = HERE / "spot.db"
    if db.exists():
        db.unlink()
    con = sqlite3.connect(db)
    con.executescript((HERE / "schema.sql").read_text())
    cars = []
    for i, (make, model) in enumerate(MAKES * 2):
        serial = f"CAR{i+1:03d}"
        cars.append((serial, make, model, 28.0 + i, 20000 + i * 5000))
    con.executemany("INSERT INTO dealerships VALUES (?,?,?,?,?)", DEALERS)
    con.executemany("INSERT INTO cars VALUES (?,?,?,?,?)", cars)
    sales = []
    # 30 sales: 2021 and 2022, prices chosen so totals are hand-checkable in tests
    for i in range(30):
        year = 2021 if i < 12 else 2022
        sales.append((i + 1, cars[i % len(cars)][0], DEALERS[i % 3][0], 1000 + (i % 7),
                      20000 + (i % 5) * 1000, f"{year}-{(i % 12) + 1:02d}-15",
                      "cash" if i % 3 == 0 else "financing", "loan" if i % 3 != 0 else None))
    con.executemany("INSERT INTO sales VALUES (?,?,?,?,?,?,?,?)", sales)
    services = []
    for i in range(40):
        services.append((i + 1, cars[i % len(cars)][0], "Auto Service Center" if i % 2 == 0 else "Auto Repair Center",
                         "engine" if i % 3 == 0 else "battery" if i % 3 == 1 else "tyre",
                         150 + (i % 4) * 50, f"20{21 + (i % 2)}-{(i % 12) + 1:02d}-10",
                         1 if i % 4 == 0 else 0, 500 + (i % 3)))
    con.executemany("INSERT INTO service_records VALUES (?,?,?,?,?,?,?,?)", services)
    con.commit()
    print(f"seeded: cars={len(cars)} dealerships={len(DEALERS)} sales={len(sales)} services={len(services)}")
    con.close()
if __name__ == "__main__":
    main()
