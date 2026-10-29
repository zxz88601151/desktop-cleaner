"""Undo-layer regressions (audit 2026-10-16) — ui.undo.run_undo contract.

Covers three defects found by the code audit, all reachable from the four
undo launch sites (完成页 / 首页 / 整理历史 / 空文件夹清理):

* D-undo-stats   ``run_undo`` rewrote ``organized_files`` / ``skipped_files``
                 to 0 when marking a history ``undone``, so the history page
                 showed "整理 0 个" and the dashboard cumulative total dropped.
* D-undo-match   ``apply_undo_result`` matched restores by the *restore
                 destination*; a restore renamed by ``_unique_target`` (the
                 original spot was occupied) stayed ``moved`` under an
                 ``undone`` history.
* D-undo-reentry Four per-page busy guards cannot see each other (each page
                 only checks its own worker), so two pages could run
                 ``run_undo`` for the same record concurrently. The guard now
                 lives here, at the single funnel all four sites call.

Importing ``ui.undo`` pulls in PySide6 (its module-level imports), but no
widget is instantiated: these tests run without a QApplication.

Run:  python -m pytest -q tests/test_undo_safety.py
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

_TMP_HOME = tempfile.mkdtemp(prefix="dc_undo_")
os.environ["DESKTOP_CLEANER_HOME"] = _TMP_HOME

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core import organize  # noqa: E402
from data import database, history_repo, operation_repo  # noqa: E402
from ui import undo as undo_mod  # noqa: E402

database.init_db()


def _organize_run(names, contents=None) -> tuple[int, Path]:
    """Organize files in a fresh folder and record a done history."""
    src = Path(tempfile.mkdtemp(prefix="dc_undo_src_"))
    for i, name in enumerate(names):
        (src / name).write_bytes(
            contents[i] if contents else name.encode()
        )
    r = organize(src, mode="type")
    assert r.moved == len(names) and r.failed == 0
    hid = history_repo.create(str(src), "type", len(names))
    operation_repo.bulk_insert(hid, r.items)
    history_repo.update_status(hid, "done", r.moved, r.skipped)
    return hid, src


@pytest.fixture(autouse=True)
def _reset_undo_flag():
    undo_mod._undo_in_progress = False
    yield
    undo_mod._undo_in_progress = False


# --------------------------------------------------------------------------- #
def test_undo_preserves_history_counters():
    """An undo flips the status, never the run's own counters."""
    hid, src = _organize_run(["a.jpg", "b.pdf", "c.mp3"])
    before = history_repo.get(hid)
    assert before["organized_files"] == 3

    out = undo_mod.run_undo(hid)

    assert out["failed_files"] == []
    after = history_repo.get(hid)
    assert after["status"] == "undone"
    assert after["organized_files"] == before["organized_files"]
    assert after["skipped_files"] == before["skipped_files"]


def test_renamed_restore_is_marked_undone():
    """A restore renamed by a collision still maps back to its operation."""
    hid, src = _organize_run(["y.txt"])
    # Occupy the original spot so the restore is renamed to "y (1).txt".
    (src / "y.txt").write_bytes(b"RECREATED")

    out = undo_mod.run_undo(hid)

    assert out["result"].moved == 1
    assert out["failed_files"] == []
    statuses = {o["status"] for o in operation_repo.list_by_history(hid)}
    assert statuses == {"undone"}, f"statuses: {statuses}"
    assert history_repo.get(hid)["status"] == "undone"


def test_concurrent_undo_is_rejected_until_the_first_finishes():
    """A second run_undo while one is in flight raises instead of racing."""
    hid, _src = _organize_run(["a.jpg", "b.pdf"])

    undo_mod._undo_in_progress = True
    with pytest.raises(ValueError, match="还原操作正在进行中"):
        undo_mod.run_undo(hid)
    # The rejected call must not have touched the record.
    assert history_repo.get(hid)["status"] == "done"


def test_undo_flag_resets_after_success_and_failure():
    """The in-flight guard must not wedge future undos."""
    hid1, _src1 = _organize_run(["a.jpg"])
    undo_mod.run_undo(hid1)
    assert undo_mod._undo_in_progress is False

    hid2, _src2 = _organize_run(["b.jpg"])
    undo_mod.run_undo(hid2)
    assert history_repo.get(hid2)["status"] == "undone"
    assert undo_mod._undo_in_progress is False


def test_undone_record_is_not_undoable_again():
    """run_undo refuses a record that is not 'done' (idempotence guard)."""
    hid, _src = _organize_run(["a.jpg"])
    undo_mod.run_undo(hid)
    with pytest.raises(ValueError, match="不可撤销"):
        undo_mod.run_undo(hid)


def teardown_module(module):
    shutil.rmtree(_TMP_HOME, ignore_errors=True)
