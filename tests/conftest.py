"""Pytest shared fixtures — P1-2 database isolation.

Root cause (2026-08-31 audit): `data.database.DB_PATH` is computed at module
import time. Under a full `pytest` run every test module is imported during
collection, so a module-level `os.environ["DESKTOP_CLEANER_HOME"]` only affects
the FIRST module that imports `data.database`; later modules share that cached
path and their env assignments are silently ignored. That polluted
`test_legacy_db_wal_upgrade` (29 passed / 1 failed full-run, PASS standalone).

Fix: an autouse fixture that re-points the DB to the *current test module's*
own `_TMP_HOME` (module-level temp dir, already set by every test file) right
before each test runs, and ensures the schema exists there. This makes every
test independent of import/collection order without touching production code
paths (`database.configure()` is never called by the app).

Each test module must define `_TMP_HOME` at module level (all existing suites
do); modules without it are left untouched.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# conftest.py is imported by pytest before any test module runs, so the
# per-module `sys.path.insert` in the test files has NOT happened yet. Make
# the project's `src/` importable here explicitly.
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from data import database


@pytest.fixture(autouse=True)
def _isolate_db(request):
    """Point the DB at this test module's temp HOME before each test."""
    home = getattr(request.module, "_TMP_HOME", None)
    if home is not None:
        database.configure(home)
        database.init_db()
    yield
