"""Build the synthetic demo database."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from arfa_aapa.data.database import DEFAULT_DB_PATH
from arfa_aapa.data.seed import build_demo_db


def main() -> None:
    path = build_demo_db(DEFAULT_DB_PATH, force=True)
    print(f"Demo database built: {path}")


if __name__ == "__main__":
    main()
