"""Deterministic synthetic demo data, shaped like a 4S business.

No real Vo Technology data, no customer names, no phones, no salaries.
Every value is generated from seed 42, so the demo is reproducible.
"""

import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

BRANCHES = [(1, "القاهرة الجديدة", "Cairo"), (2, "الجيزة", "Giza"), (3, "الإسكندرية", "Alexandria")]
MODELS = ["Sedan A", "SUV B", "Hatchback C", "Pickup D"]
PARTS = [
    ("فلتر زيت", 350),
    ("تيل فرامل", 1200),
    ("بطارية", 4500),
    ("إطار", 2800),
    ("بوجيهات", 600),
    ("مساعدين", 3200),
]
SERVICE_TYPES = ["صيانة دورية", "فرامل", "كهرباء", "عفشة", "تكييف"]


def _dates(start: date, end: date, count: int, rng: random.Random) -> list[date]:
    span = (end - start).days
    return [start + timedelta(days=rng.randint(0, span)) for _ in range(count)]


def build_demo_db(db_path: Path, force: bool = False) -> Path:
    db_path = Path(db_path)
    if db_path.exists() and not force:
        raise FileExistsError(f"Database already exists: {db_path}. Use force=True to rebuild.")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    rng = random.Random(42)
    start, end = date(2026, 1, 1), date(2026, 10, 27)
    connection = sqlite3.connect(db_path)
    try:
        connection.executescript(
            """
            CREATE TABLE branches (id INTEGER PRIMARY KEY, name TEXT NOT NULL, city TEXT NOT NULL);
            CREATE TABLE sales (id INTEGER PRIMARY KEY, branch_id INTEGER NOT NULL, sale_date TEXT NOT NULL, vehicle_model TEXT NOT NULL, amount_egp REAL NOT NULL, status TEXT NOT NULL);
            CREATE TABLE service_job_cards (id INTEGER PRIMARY KEY, branch_id INTEGER NOT NULL, opened_date TEXT NOT NULL, closed_date TEXT, status TEXT NOT NULL, service_type TEXT NOT NULL, labor_amount_egp REAL NOT NULL, sold_hours REAL NOT NULL, actual_hours REAL NOT NULL);
            CREATE TABLE parts_sales (id INTEGER PRIMARY KEY, branch_id INTEGER NOT NULL, sale_date TEXT NOT NULL, part_name TEXT NOT NULL, quantity INTEGER NOT NULL, amount_egp REAL NOT NULL);
            CREATE TABLE parts_inventory (id INTEGER PRIMARY KEY, branch_id INTEGER NOT NULL, part_name TEXT NOT NULL, stock_qty INTEGER NOT NULL, reorder_level INTEGER NOT NULL);
            CREATE TABLE surveys (id INTEGER PRIMARY KEY, branch_id INTEGER NOT NULL, survey_date TEXT NOT NULL, score_1_5 INTEGER NOT NULL);
            """
        )
        connection.executemany("INSERT INTO branches VALUES (?, ?, ?)", BRANCHES)

        for i, sale_date in enumerate(_dates(start, end, 180, rng), start=1):
            status = "invoiced" if rng.random() < 0.85 else "cancelled"
            connection.execute(
                "INSERT INTO sales VALUES (?, ?, ?, ?, ?, ?)",
                (i, rng.choice(BRANCHES)[0], sale_date.isoformat(), rng.choice(MODELS), rng.randint(350000, 1200000), status),
            )

        for i, opened in enumerate(_dates(start, end, 420, rng), start=1):
            status = rng.choices(
                ["open", "ready", "invoiced", "closed"], weights=[25, 20, 30, 25]
            )[0]
            closed = (opened + timedelta(days=rng.randint(1, 12))).isoformat() if status in ("invoiced", "closed") else None
            sold = round(rng.uniform(1, 8), 1)
            connection.execute(
                "INSERT INTO service_job_cards VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (i, rng.choice(BRANCHES)[0], opened.isoformat(), closed, status, rng.choice(SERVICE_TYPES), rng.randint(800, 12000), sold, round(sold * rng.uniform(0.8, 1.3), 1)),
            )

        for i, sale_date in enumerate(_dates(start, end, 600, rng), start=1):
            part, price = rng.choice(PARTS)
            quantity = rng.randint(1, 4)
            connection.execute(
                "INSERT INTO parts_sales VALUES (?, ?, ?, ?, ?, ?)",
                (i, rng.choice(BRANCHES)[0], sale_date.isoformat(), part, quantity, quantity * price),
            )

        row_id = 1
        for branch_id, _, _ in BRANCHES:
            for part, _ in PARTS:
                connection.execute(
                    "INSERT INTO parts_inventory VALUES (?, ?, ?, ?, ?)",
                    (row_id, branch_id, part, rng.randint(0, 40), 8),
                )
                row_id += 1

        for i, survey_date in enumerate(_dates(start, end, 300, rng), start=1):
            score = rng.choices([3, 4, 5], weights=[20, 45, 35])[0]
            connection.execute(
                "INSERT INTO surveys VALUES (?, ?, ?, ?)",
                (i, rng.choice(BRANCHES)[0], survey_date.isoformat(), score),
            )
        connection.commit()
    finally:
        connection.close()
    return db_path
