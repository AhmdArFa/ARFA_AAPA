"""Thin wrapper. Canonical seed logic is scripts/seed_company.py.

This script runs the canonical seed, which builds data/company.db,
then copies it to experiments/company-domains/company.db, so experiments
tests that open the local company.db directly still work. Do not edit
seed logic here.
"""
import shutil, subprocess, sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def main():
    subprocess.run([sys.executable, str(_REPO_ROOT / "scripts" / "seed_company.py")], check=True, cwd=str(_REPO_ROOT))
    src_db = _REPO_ROOT / "data" / "company.db"
    dst_db = Path(__file__).resolve().parent / "company.db"
    shutil.copyfile(src_db, dst_db)
    print(f"company.db copied to {dst_db}")


if __name__ == "__main__":
    main()
