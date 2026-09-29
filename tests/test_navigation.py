"""V1.2-A-CLOSURE — navigation regression lock (offscreen Qt).

Run:  pytest tests/test_navigation.py
  or: QT_QPA_PLATFORM=offscreen python tests/test_navigation.py

Purpose
-------
Freeze the *navigation contract* so a later refactor cannot silently drop,
rename or reorder the product's pages. This is a lock, not a feature: it adds
no UI and changes no behaviour.

Why the contract is a SET + relative ORDER, not an absolute count
-----------------------------------------------------------------
PHASE 1.2 adds its own "large" (大文件) entry, which is deliberately **not**
part of the V1.2-A baseline commit. An absolute "7 entries" assertion would
therefore fail in the V1.2-A commit tree (6 entries) while passing in the
current working tree (7 entries) — the lock must hold in *both*. So it pins:

  - the presence of every V1.2-A-era nav id,
  - their **relative order**,
  - the default landing page,
  - page registration + routing for every page-backed nav entry,
  - the V1.2-A display labels (so a silent rename fails),
  - the absence of duplicates,
  - the bottom "关于" entry (a modal dialog, not a stacked page).

Anything else (e.g. PHASE 1.2's extra entry) may be present without breaking
the lock.
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_TMP_HOME = tempfile.mkdtemp(prefix="dc_nav_")
os.environ["DESKTOP_CLEANER_HOME"] = _TMP_HOME

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from data import database, settings_repo  # noqa: E402
from ui.widgets import sidebar as sidebar_mod  # noqa: E402

# --------------------------------------------------------------------------- #
# the locked contract
# --------------------------------------------------------------------------- #
#: Nav ids that must exist, in this exact relative order.
REQUIRED_NAV = ["organize", "analysis", "empty", "history", "settings", "rules"]

#: Display labels owned by V1.2-A (a rename must fail loudly).
V1_2_A_LABELS = {
    "analysis": "文件夹分析",
    "empty": "空文件夹",
    "rules": "自定义规则",
}

#: The product's default landing page (UI-1.3 Phase 1.5: 整理 is Product Home).
DEFAULT_LANDING = "organize"

#: The bottom nav group — "about" is a modal dialog, not a stacked page.
BOTTOM_NAV = ["about"]

#: Pages that must stay registered even though they are not on the sidebar
#: (immutable registry contract asserted by tests/test_appshell.py).
OFF_NAV_PAGES = ["home", "custom"]


def _app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication(sys.argv)


def _shell():
    """Build a headless AppShell with the welcome dialog suppressed."""
    _app()
    database.init_db()
    settings_repo.set("first_launch_completed", 1)
    from ui.app_shell import AppShell

    return AppShell()


def _nav_ids(shell) -> list:
    """Nav ids in sidebar order (dicts preserve insertion order)."""
    return list(shell.sidebar._buttons.keys())


def _page_nav_ids(shell) -> list:
    """Nav ids that are stacked pages (excludes the modal 'about' entry)."""
    return [pid for pid in _nav_ids(shell) if pid in shell._pages]


def _assert(cond: bool, msg: str):
    if not cond:
        raise AssertionError("FAIL: " + msg)
    print("  ok:", msg)


# --------------------------------------------------------------------------- #
# tests
# --------------------------------------------------------------------------- #
def test_nav_entries_present_in_fixed_relative_order():
    shell = _shell()
    ids = [pid for pid in _nav_ids(shell) if pid in REQUIRED_NAV]
    assert ids == REQUIRED_NAV, f"nav contract order broken: {ids} != {REQUIRED_NAV}"
    all_ids = _nav_ids(shell)
    assert len(all_ids) == len(set(all_ids)), "duplicate nav id"
    # NOTE: PHASE 1.2's "large" entry may also be present; that is allowed and
    # intentionally not asserted here (it is not part of the V1.2-A baseline).
    print("  ok: nav contract present and in fixed relative order:", ids)


def test_declared_nav_matches_sidebar_widget():
    """`_NAV` (declaration) and the built main-group buttons must agree."""
    shell = _shell()
    declared = [pid for pid, _icon, _label in sidebar_mod._NAV]
    bottom = {pid for pid, _icon, _label in sidebar_mod._BOTTOM}
    built_main = [pid for pid in _nav_ids(shell) if pid not in bottom]
    assert declared == built_main, f"declared {declared} != built {built_main}"
    print("  ok: sidebar._NAV declaration matches the built main-group buttons")


def test_v12a_labels_are_fixed():
    shell = _shell()
    labels = {pid: label for pid, _icon, label in sidebar_mod._NAV}
    for pid, expected in V1_2_A_LABELS.items():
        assert labels.get(pid) == expected, (
            f"label for {pid!r} changed: {labels.get(pid)!r} != {expected!r}"
        )
    print("  ok: V1.2-A nav labels fixed:", V1_2_A_LABELS)


def test_default_landing_is_fixed():
    shell = _shell()
    assert shell.stack.currentWidget() is shell._pages[DEFAULT_LANDING], (
        "default landing page is not " + DEFAULT_LANDING
    )
    print(f"  ok: default landing page is {DEFAULT_LANDING!r}")


def test_every_page_nav_entry_is_registered_and_routable():
    shell = _shell()
    from ui.app_shell import _TITLES

    ids = _page_nav_ids(shell)
    assert set(REQUIRED_NAV) <= set(ids), f"missing page-backed nav: {REQUIRED_NAV}"
    for pid in ids:
        assert pid in _TITLES, f"nav {pid!r} has no title"
        shell._route(pid)
        assert shell.stack.currentWidget() is shell._pages[pid], (
            f"routing to {pid!r} did not select its page"
        )
        enter = getattr(shell._pages[pid], "on_enter", None)
        if callable(enter):
            enter()
    print("  ok: all", len(ids), "page-backed nav entries registered + routable")


def test_clicking_a_nav_button_navigates():
    shell = _shell()
    seen = []
    shell.sidebar.navigate.connect(lambda pid: seen.append(pid))
    for pid in _page_nav_ids(shell):
        shell.sidebar._buttons[pid].click()
        assert seen[-1] == pid, f"clicking {pid!r} emitted {seen[-1]!r}"
        assert shell.stack.currentWidget() is shell._pages[pid], (
            f"clicking {pid!r} did not route"
        )
    print("  ok: every page-backed nav button click routes to its page")


def test_bottom_nav_is_a_dialog_not_a_page():
    shell = _shell()
    bottom = [pid for pid, _icon, _label in sidebar_mod._BOTTOM]
    assert bottom == BOTTOM_NAV, f"bottom nav changed: {bottom}"
    for pid in bottom:
        assert pid in shell.sidebar._buttons, f"bottom nav {pid!r} not built"
        assert pid not in shell._pages, (
            f"{pid!r} must stay a modal dialog, not a stacked page"
        )
    print("  ok: bottom nav intact and dialog-only:", bottom)


def test_off_nav_pages_still_registered():
    """Pages that are not on the sidebar must still exist (immutable contract)."""
    shell = _shell()
    for pid in OFF_NAV_PAGES:
        assert pid in shell._pages, f"page {pid!r} disappeared from the registry"
    print("  ok: non-sidebar pages still registered:", OFF_NAV_PAGES)


def main():
    test_nav_entries_present_in_fixed_relative_order()
    test_declared_nav_matches_sidebar_widget()
    test_v12a_labels_are_fixed()
    test_default_landing_is_fixed()
    test_every_page_nav_entry_is_registered_and_routable()
    test_clicking_a_nav_button_navigates()
    test_bottom_nav_is_a_dialog_not_a_page()
    test_off_nav_pages_still_registered()
    print("\nALL NAVIGATION REGRESSION TESTS PASSED")


if __name__ == "__main__":
    main()
