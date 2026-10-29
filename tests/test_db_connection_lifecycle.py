"""SQLite connection lifecycle regression tests (P1: `data.connection()`).

Background
----------
``get_connection()`` returns a bare ``sqlite3.Connection``. Written as
``with get_connection() as conn:`` it invokes the *transaction* context manager,
which commits on success and rolls back on exception but never closes. Every
production call site therefore leaked a handle until the garbage collector
happened to reclaim it (a connection that has executed a statement sits in a
reference cycle, so refcounting alone never frees it).

``data.database.connection()`` keeps those transaction semantics and adds a
deterministic ``close()``. These tests pin down the resulting contract:

* closed after a normal exit
* closed after an exceptional exit
* the original exception is never replaced or suppressed
* a close failure is loud when nothing else failed, and silent-but-preserved
  when an application exception is already propagating
* "nothing else failed" is decided from the block itself, never from the
  call-stack handler context (see the ``except``-handler regression test)
* commit / rollback / multi-statement atomicity are unchanged
* ``get_connection()`` still hands back an open raw connection
* every one of the 16 migrated call sites closes its connection

Isolation: tests that need two connections to observe each other use the
isolated temp HOME provided by ``tests/conftest.py`` (never the repository
``data/`` directory). Tests that only exercise context-manager mechanics use
throwaway in-memory databases.

Run:  python -m pytest -q tests/test_db_connection_lifecycle.py
"""
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

_TMP_HOME = tempfile.mkdtemp(prefix="dc_dbconn_")
os.environ["DESKTOP_CLEANER_HOME"] = _TMP_HOME

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core.organizer import OrganizeResult, PlanItem  # noqa: E402
from data import database  # noqa: E402
from data import history_repo, operation_repo, settings_repo  # noqa: E402


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
class _CloseBoom(sqlite3.Connection):
    """Connection whose *first* close() raises, later closes behave normally.

    The one-shot behaviour keeps the test honest: the first close is the one
    under test, while any close performed later during interpreter cleanup
    succeeds and does not pollute the run with ignored exceptions.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._boom_pending = True

    def close(self):
        if self._boom_pending:
            self._boom_pending = False
            raise RuntimeError("close failed")
        super().close()


def _use_in_memory(monkeypatch):
    """Make `database.get_connection()` hand out throwaway in-memory DBs."""
    opened = []

    def fake_get_connection():
        conn = sqlite3.connect(":memory:")
        opened.append(conn)
        return conn

    monkeypatch.setattr(database, "get_connection", fake_get_connection)
    return opened


def _counting_connections(monkeypatch):
    """Patch ``database.get_connection`` with an open/close counting factory.

    ``connection()`` resolves ``get_connection`` as a module global, so patching
    it here also covers every repo that routes through ``connection()``.
    """
    counts = {"opened": 0, "closed": 0}

    class _Counting(sqlite3.Connection):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._open = True
            counts["opened"] += 1

        def close(self):
            if self._open:
                self._open = False
                counts["closed"] += 1
            super().close()

    db_path = str(database.DB_PATH)

    def fake_get_connection():
        # Mirror the real get_connection() closely enough for the repos to work:
        # the row_factory matters, because callers index rows by column name.
        conn = sqlite3.connect(db_path, timeout=30, factory=_Counting)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(database, "get_connection", fake_get_connection)
    return counts


def _assert_no_leak(counts, expected):
    assert counts["opened"] == expected, (
        f"expected {expected} connections, opened {counts['opened']}"
    )
    assert counts["closed"] == expected, (
        f"leaked {counts['opened'] - counts['closed']} connections"
    )


def _item(name, target_dir, source_dir):
    """A PlanItem whose paths live entirely inside the isolated temp HOME."""
    return PlanItem(
        source=Path(_TMP_HOME) / source_dir / name,
        target=Path(_TMP_HOME) / target_dir / name,
        category="图片",
    )


_TRIGGER = "db_conn_boom"


def _install_failing_update_trigger():
    """Abort (from inside SQLite) any UPDATE that would set status='failed'.

    Using a trigger rather than monkeypatching keeps the failure *inside* the
    transaction, which is the only way to observe a mid-transaction rollback.
    """
    raw = database.get_connection()
    try:
        raw.execute(
            f"CREATE TRIGGER {_TRIGGER} BEFORE UPDATE ON operations "
            "WHEN NEW.status = 'failed' "
            "BEGIN SELECT RAISE(ABORT, 'db_conn_forced'); END"
        )
        raw.commit()
    finally:
        raw.close()


def _drop_failing_update_trigger():
    raw = database.get_connection()
    try:
        raw.execute(f"DROP TRIGGER IF EXISTS {_TRIGGER}")
        raw.commit()
    finally:
        raw.close()


def _read_setting(key):
    """Read one setting through a manually managed raw connection."""
    raw = database.get_connection()
    try:
        row = raw.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None
    finally:
        raw.close()


def _write_setting(key, value):
    with database.connection() as conn:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


# --------------------------------------------------------------------------- #
# closure
# --------------------------------------------------------------------------- #
def test_connection_closes_on_normal_exit(monkeypatch):
    _use_in_memory(monkeypatch)
    with database.connection() as conn:
        conn.execute("CREATE TABLE t(x)")
        conn.execute("INSERT INTO t VALUES (1)")
        assert conn.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 1
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("SELECT 1")


def test_connection_closes_on_exceptional_exit(monkeypatch):
    _use_in_memory(monkeypatch)
    with pytest.raises(RuntimeError):
        with database.connection() as conn:
            conn.execute("CREATE TABLE t(x)")
            raise RuntimeError("boom")
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("SELECT 1")


def test_original_exception_is_not_suppressed(monkeypatch):
    _use_in_memory(monkeypatch)
    sentinel = KeyError("original")
    with pytest.raises(KeyError) as caught:
        with database.connection() as conn:
            raise sentinel
    assert caught.value is sentinel


# --------------------------------------------------------------------------- #
# close failures
# --------------------------------------------------------------------------- #
def test_close_failure_is_raised_when_nothing_else_failed(monkeypatch):
    monkeypatch.setattr(
        database,
        "get_connection",
        lambda: sqlite3.connect(":memory:", factory=_CloseBoom),
    )
    with pytest.raises(RuntimeError, match="close failed"):
        with database.connection() as conn:
            conn.execute("SELECT 1")


def test_close_failure_does_not_replace_active_exception(monkeypatch):
    monkeypatch.setattr(
        database,
        "get_connection",
        lambda: sqlite3.connect(":memory:", factory=_CloseBoom),
    )
    sentinel = ValueError("application error")
    with pytest.raises(ValueError) as caught:
        with database.connection() as conn:
            raise sentinel
    assert caught.value is sentinel, "close() error replaced the application error"


def test_close_failure_is_loud_even_inside_an_except_handler(monkeypatch):
    """Regression: "is anything in flight?" must not consult the call stack.

    Entering the context manager from inside an ``except`` block used to make
    ``sys.exc_info()`` non-None even on a *clean* exit, so the close failure was
    swallowed silently and the handle could stay open unnoticed.
    """
    monkeypatch.setattr(
        database,
        "get_connection",
        lambda: sqlite3.connect(":memory:", factory=_CloseBoom),
    )
    try:
        raise KeyError("outer")
    except KeyError:
        with pytest.raises(RuntimeError, match="close failed"):
            with database.connection() as conn:
                conn.execute("SELECT 1")


def test_close_failure_does_not_replace_a_commit_failure(monkeypatch):
    """An error raised on the way out of the transaction is also "in flight".

    This is the only case where two different errors compete: the commit fails,
    and then the close fails too. The commit error must win.

    The commit failure is a *real* one — a foreign-key violation deferred to
    COMMIT time — rather than a stubbed ``commit()``. Stubbing would not work:
    ``sqlite3.Connection.__exit__`` calls the C-level commit implementation
    directly and therefore bypasses any Python-level ``commit()`` override.
    """
    raw = database.get_connection()
    try:
        raw.execute("CREATE TABLE IF NOT EXISTS boom_parent(id INTEGER PRIMARY KEY)")
        raw.execute(
            "CREATE TABLE IF NOT EXISTS boom_child("
            "  id  INTEGER PRIMARY KEY,"
            "  pid INTEGER REFERENCES boom_parent(id) DEFERRABLE INITIALLY DEFERRED)"
        )
        raw.commit()
    finally:
        raw.close()

    db_path = str(database.DB_PATH)

    def fake_get_connection():
        conn = sqlite3.connect(db_path, timeout=30, factory=_CloseBoom)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    monkeypatch.setattr(database, "get_connection", fake_get_connection)

    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        with database.connection() as conn:
            # Accepted now, rejected by the deferred constraint at COMMIT.
            conn.execute("INSERT INTO boom_child(id, pid) VALUES (1, 999)")


# --------------------------------------------------------------------------- #
# transaction semantics (isolated temp HOME, never the repository data/ dir)
# --------------------------------------------------------------------------- #
def test_commit_is_visible_to_a_second_connection():
    _write_setting("db_conn_commit", "committed")
    assert _read_setting("db_conn_commit") == "committed"


def test_rollback_is_effective_when_the_body_raises():
    with pytest.raises(RuntimeError):
        with database.connection() as conn:
            conn.execute(
                "INSERT INTO settings(key, value) VALUES(?, ?)",
                ("db_conn_rollback", "should-not-survive"),
            )
            raise RuntimeError("abort")
    assert _read_setting("db_conn_rollback") is None


def test_multi_statement_atomicity_preserved():
    with database.connection() as conn:
        conn.execute("INSERT INTO settings(key, value) VALUES('db_conn_a', '1')")
        conn.execute("INSERT INTO settings(key, value) VALUES('db_conn_b', '2')")
    assert _read_setting("db_conn_a") == "1"
    assert _read_setting("db_conn_b") == "2"

    with pytest.raises(RuntimeError):
        with database.connection() as conn:
            conn.execute("INSERT INTO settings(key, value) VALUES('db_conn_c', '3')")
            conn.execute("INSERT INTO settings(key, value) VALUES('db_conn_d', '4')")
            raise RuntimeError("abort")
    assert _read_setting("db_conn_c") is None
    assert _read_setting("db_conn_d") is None


# --------------------------------------------------------------------------- #
# get_connection() public contract must be unchanged
# --------------------------------------------------------------------------- #
def test_get_connection_returns_open_raw_connection():
    conn = database.get_connection()
    assert type(conn) is sqlite3.Connection, "get_connection() must not be wrapped"
    try:
        conn.execute("SELECT 1")
        conn.execute("SELECT 1")
        conn.commit()
    finally:
        conn.close()
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("SELECT 1")


# --------------------------------------------------------------------------- #
# deterministic leak guard (open/close accounting, not a GC object count)
#
# One guard per module, so every one of the 16 migrated call sites is covered by
# an executed assertion rather than by "same pattern, presumably fine".
# --------------------------------------------------------------------------- #
def test_settings_repo_closes_its_connections(monkeypatch):
    counts = _counting_connections(monkeypatch)
    for i in range(20):
        settings_repo.set(f"db_conn_leak_{i}", "v")
        settings_repo.get(f"db_conn_leak_{i}")
    _assert_no_leak(counts, 40)


def test_init_db_closes_its_connection(monkeypatch):
    counts = _counting_connections(monkeypatch)
    database.init_db()
    _assert_no_leak(counts, 1)


def test_history_repo_closes_every_connection(monkeypatch):
    counts = _counting_connections(monkeypatch)
    hid = history_repo.create(str(_TMP_HOME), "type", 0)
    history_repo.update_status(hid, "done", 1, 0)
    history_repo.get(hid)
    history_repo.list_all()
    history_repo.latest_done()
    history_repo.get_stats()
    _assert_no_leak(counts, 6)


def test_operation_repo_closes_every_connection(monkeypatch):
    # Seeded with real connections, before the counter is installed.
    hid = history_repo.create(str(_TMP_HOME), "type", 0)
    items = [
        _item("a.jpg", "图片", "src_ops"),
        _item("b.jpg", "图片", "src_ops"),
    ]

    counts = _counting_connections(monkeypatch)
    operation_repo.bulk_insert(hid, items)
    operation_repo.bulk_insert_pending(hid, items)
    operation_repo.update_statuses_by_target(hid, {str(items[0].target)}, set())
    operation_repo.apply_undo_result(hid, OrganizeResult(items=list(items)))
    operation_repo.reconcile_pending()
    operation_repo.list_by_history(hid)
    operation_repo.update_status(1, "moved")
    _assert_no_leak(counts, 7)


def test_reconcile_pending_rolls_back_a_midway_failure(monkeypatch):
    """Repo-level atomicity, and closure on the failure path.

    ``reconcile_pending()`` settles many rows inside one transaction. A failure
    part-way through must undo the rows already settled in that same call, and
    must still close the connection.
    """
    hid = history_repo.create(str(_TMP_HOME), "type", 0)

    # Two ops that reconcile to 'moved' (target present, source gone) ...
    items = []
    for name in ("m1.jpg", "m2.jpg"):
        it = _item(name, "restored", "src_absent")
        it.target.parent.mkdir(parents=True, exist_ok=True)
        it.target.write_bytes(b"x")
        items.append(it)

    # ... followed by one that reconciles to 'failed' (source still present),
    # which is the statement the trigger aborts.
    stuck = _item("stuck.jpg", "restored", "src_stuck")
    stuck.source.parent.mkdir(parents=True, exist_ok=True)
    stuck.source.write_bytes(b"x")
    items.append(stuck)

    operation_repo.bulk_insert_pending(hid, items)

    _install_failing_update_trigger()
    try:
        counts = _counting_connections(monkeypatch)
        with pytest.raises(sqlite3.DatabaseError, match="db_conn_forced"):
            operation_repo.reconcile_pending()
        _assert_no_leak(counts, 1)
    finally:
        _drop_failing_update_trigger()

    statuses = [op["status"] for op in operation_repo.list_by_history(hid)]
    assert statuses == ["pending"] * 3, f"transaction not rolled back: {statuses}"
