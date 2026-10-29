"""Pytest shared fixtures — test isolation for the database and log paths.

Two distinct isolation problems are handled in this file.

1. Import-time path binding (fixed 2026-10-09).

   ``data.database`` resolves ``DB_DIR`` / ``DB_PATH`` from
   ``DESKTOP_CLEANER_HOME`` **when the module is first imported**
   (database.py:25-27), and ``utils.logger`` binds each ``FileHandler`` to
   ``DB_DIR/desktop_cleaner.log`` on the first ``get_logger()`` call
   (logger.py:14-17). pytest imports ``conftest.py`` before any test module, so
   this file used to import ``data.database`` while ``DESKTOP_CLEANER_HOME`` was
   still unset; the path fell back to the project root. Seven test modules call
   ``init_db()`` at module scope, i.e. during collection and therefore before any
   fixture runs, so every run wrote the schema into
   ``<repo>/data/desktop_cleaner.db`` and bound seven ``FileHandler``s to
   ``<repo>/data/desktop_cleaner.log``.

   Fix: the isolated HOME is established *above* the ``data`` import, so
   collection-time path binding can only ever see the test HOME.

   Default behaviour is a fresh, dedicated test-isolation directory under the
   system temp dir. An inherited ``DESKTOP_CLEANER_HOME`` is deliberately
   overwritten rather than honoured: an inherited value cannot be distinguished
   from an accidental one (e.g. a shell profile exporting it), and silently
   honouring it would send test writes to an arbitrary location while the run
   still reported itself as isolated.

   A caller who intentionally wants a specific HOME sets the separate opt-in
   variable ``DESKTOP_CLEANER_TEST_HOME``. Because it is a different variable
   from the one the application reads, setting it cannot happen by accident.
   That mode is honoured, and it announces itself: isolation is explicitly not
   claimed for an external HOME.

2. Per-test-module DB re-pointing (P1-2, fixed 2026-08-31).

   ``DB_PATH`` is computed at module import time, so under a full ``pytest`` run
   every test module is imported during collection and a module-level
   ``os.environ["DESKTOP_CLEANER_HOME"]`` only affects the FIRST module that
   imports ``data.database``; later modules share that cached path and their env
   assignments are silently ignored. That polluted ``test_legacy_db_wal_upgrade``
   (29 passed / 1 failed full-run, PASS standalone).

   Fix: an autouse fixture that re-points the DB to the *current test module's*
   own ``_TMP_HOME`` (module-level temp dir, already set by every test file)
   right before each test runs, and ensures the schema exists there. This makes
   every test independent of import/collection order without touching production
   code paths (``database.configure()`` is never called by the app).

   Each test module must define ``_TMP_HOME`` at module level (all existing
   suites do); modules without it are left untouched.
"""
from __future__ import annotations

import os
import sys
import tempfile
import warnings
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Isolation bootstrap. This block MUST stay above every application import
# below: `data.database` binds its paths at import time, so the environment has
# to be correct before that import is evaluated.
# ---------------------------------------------------------------------------

#: Opt-in variable for running the suite against a caller-chosen HOME. Kept
#: distinct from the variable the application reads so that it can only ever be
#: set deliberately, never inherited by accident.
EXTERNAL_HOME_ENV = "DESKTOP_CLEANER_TEST_HOME"

#: Name prefix of the throwaway directory used for a normal, isolated run.
ISOLATION_DIR_PREFIX = "dc_pytest_home_"

#: Value of DESKTOP_CLEANER_HOME before this module touched it. Recorded so that
#: an accidental inheritance is visible instead of silent. An empty string is
#: treated as unset, matching `database._app_base()`, which tests truthiness.
INHERITED_HOME = os.environ.get("DESKTOP_CLEANER_HOME") or None

_external_home = os.environ.get(EXTERNAL_HOME_ENV) or None

if _external_home:
    ISOLATION_MODE = "external"
    TEST_HOME = str(Path(_external_home).expanduser())
else:
    ISOLATION_MODE = "isolated"
    TEST_HOME = tempfile.mkdtemp(prefix=ISOLATION_DIR_PREFIX)

# Unconditional assignment: an inherited value is never trusted, and
# `setdefault` is deliberately not used.
os.environ["DESKTOP_CLEANER_HOME"] = TEST_HOME

if ISOLATION_MODE == "external":
    warnings.warn(
        f"{EXTERNAL_HOME_ENV} is set, so this run uses the external HOME "
        f"{TEST_HOME!r}. Database and log writes are NOT isolated from that "
        f"location. Unset {EXTERNAL_HOME_ENV} for a normal isolated run.",
        stacklevel=1,
    )
elif INHERITED_HOME is not None:
    warnings.warn(
        f"DESKTOP_CLEANER_HOME={INHERITED_HOME!r} was inherited from the "
        f"environment and has been overridden with the test-isolation HOME "
        f"{TEST_HOME!r}. Set {EXTERNAL_HOME_ENV} instead if you really meant to "
        f"run against that path.",
        stacklevel=1,
    )

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
