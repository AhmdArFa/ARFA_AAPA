"""Thin wrapper. Canonical implementation is src/arfa_aapa/hardened.py.

Do not edit rules here. Edit src/arfa_aapa/hardened.py, and this module
re-exports it, so experiments and core always use the same validator.
"""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from arfa_aapa.hardened import *  # noqa: F401,F403
from arfa_aapa.hardened import ALLOWED_COLUMNS, FORBIDDEN_WORDS, check_template, validate_hardened
