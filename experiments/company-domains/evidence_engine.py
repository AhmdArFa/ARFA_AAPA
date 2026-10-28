"""Thin wrapper. Canonical implementation is src/arfa_aapa/evidence.py.

Do not edit profit, warehouse, or employee logic here. Edit src.
This wrapper only changes the default database for experiments tests:
if experiments/company-domains/company.db exists, use it, otherwise use
the canonical logic from src.
"""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from arfa_aapa.evidence import EvidenceAnswer, EvidenceEngine as _SrcEvidenceEngine  # noqa: F401

_EXP_DB = Path(__file__).resolve().parent / "company.db"


class EvidenceEngine(_SrcEvidenceEngine):
    def __init__(self, db_path=None):
        if db_path is None and _EXP_DB.exists():
            super().__init__(_EXP_DB)
        else:
            super().__init__(db_path)
