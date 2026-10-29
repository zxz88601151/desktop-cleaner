"""Feature-registry consistency + Tools-page regression guard.

Run:  pytest tests/test_features_registry.py
  or: QT_QPA_PLATFORM=offscreen python tests/test_features_registry.py

Why this file exists
--------------------
``src/ui/features.py`` is the single source of truth for product capabilities,
and ``src/ui/pages/tools_page.py`` renders every *non-AVAILABLE* entry as a
"coming soon" card. When V1.2-A shipped 空文件夹清理 / 文件夹分析 and PHASE 1.2
shipped 大文件分析, their registry ``status`` was left at COMING_SOON / PLANNED,
so the Tools page kept advertising three already-shipped features as
"即将上线 / 规划中" — visible in the nav *and* in the coming-soon list at once.

No existing suite covered this:
  - ``test_p2_coverage.py`` has no Qt and never imports ``ui.features``;
  - ``test_navigation.py`` guards the *page* registry (``AppShell._pages``),
    not the *feature* registry.

What is asserted here
---------------------
The Tools page is really built (offscreen Qt) and its cards are read back from
the QLabels the cards actually paint. The expectation is recomputed **directly
from ``FEATURES``**, deliberately *not* via ``get_features()`` — so a divergence
between the page, the filter helper and the registry is caught instead of
being mirrored back.

Every count is derived at runtime. No literal "7" is asserted, so adding a
feature does not break this file: the contract is "the Tools page shows exactly
the non-AVAILABLE registry entries", whatever that set currently is.

Which guard catches what (verified by mutation testing)
-------------------------------------------------------
The two kinds of assertion here have *different* jobs, and neither replaces the
other:

  * the dynamic guards (``test_tools_page_shows_only_non_available_registry_
    entries``, ``test_every_painted_card_maps_to_a_real_registry_entry``,
    ``test_page_registry_comparison_is_not_vacuous``) compare the painted page
    against an expectation recomputed from ``FEATURES``. They catch a broken
    *filter or render path* -- e.g. ``get_features()`` no longer honouring
    ``status`` (4/4 caught).

  * ``test_shipped_features_are_not_advertised_on_tools_page`` pins the
    *product truth* via :data:`SHIPPED_AS_PAGE`. This is the only guard that
    catches a regression of a specific feature's status, because a status that
    is itself wrong changes both the page and the recomputed expectation in
    lockstep, leaving no page-vs-registry divergence to detect.

That hardcoded key/name map is therefore deliberate, and its purpose is
protection, not brittleness: it encodes "these three really are shipped", which
is exactly the fact that silently drifted before this file existed.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_TMP_HOME = tempfile.mkdtemp(prefix="dc_features_registry_")
os.environ["DESKTOP_CLEANER_HOME"] = _TMP_HOME

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

from ui.features import (  # noqa: E402
    FEATURES,
    FeatureDefinition,
    FeatureStatus,
    get_feature,
    get_features,
)
from ui.pages.tools_page import ToolCard, ToolsPage  # noqa: E402

#: Features shipped as their own page (V1.2-A F1/F2, PHASE 1.2). They must
#: never be advertised on the Tools / Coming Soon page.
SHIPPED_AS_PAGE = {
    "LARGE_FILES": "大文件分析",
    "EMPTY_FOLDER": "空文件夹清理",
    "FOLDER_ANALYZER": "文件夹分析",
}

_ALL_STATUSES = {
    FeatureStatus.AVAILABLE,
    FeatureStatus.COMING_SOON,
    FeatureStatus.PLANNED,
}


def _app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication(sys.argv)


def _render_tools_page():
    """Really build the Tools page; return ``[(name, badge), ...]`` as painted.

    Both values are read from the QLabels the card actually renders, so this
    exercises the real display path rather than inspecting registry data.
    """
    _app()
    page = ToolsPage()
    rows = []
    for card in page.findChildren(ToolCard):
        name = badge = ""
        for lbl in card.findChildren(QLabel):
            obj = lbl.objectName()
            if obj == "tool-name":
                name = lbl.text()
            elif obj == "tool-badge":
                badge = lbl.text()
        rows.append((name, badge))
    return page, rows


def _by_name() -> dict:
    """name -> FeatureDefinition (names are asserted unique below)."""
    return {f.name: f for f in FEATURES}


def _expected_non_available_names() -> set:
    """Recomputed from FEATURES directly -- deliberately NOT via get_features()."""
    return {f.name for f in FEATURES if f.status != FeatureStatus.AVAILABLE}


# --------------------------------------------------------------------------- #
# 1. registry loads
# --------------------------------------------------------------------------- #
def test_registry_loads():
    assert isinstance(FEATURES, list) and FEATURES, "feature registry is empty"
    for f in FEATURES:
        assert isinstance(f, FeatureDefinition), f"not a FeatureDefinition: {f!r}"
        assert f.key and f.name and f.icon and f.description, f"incomplete entry: {f!r}"
        assert f.status in _ALL_STATUSES, f"{f.key} has unknown status {f.status!r}"


# --------------------------------------------------------------------------- #
# 2. identifiers are unique
# --------------------------------------------------------------------------- #
def test_feature_keys_are_unique():
    keys = [f.key for f in FEATURES]
    assert len(keys) == len(set(keys)), f"duplicate feature key(s) in {keys}"
    names = [f.name for f in FEATURES]
    assert len(names) == len(set(names)), f"duplicate feature name(s) in {names}"


# --------------------------------------------------------------------------- #
# 3. AVAILABLE vs non-AVAILABLE classification is coherent
# --------------------------------------------------------------------------- #
def test_status_classification_is_coherent():
    for f in FEATURES:
        assert f.status in _ALL_STATUSES, f"{f.key}: {f.status!r}"
        if f.status == FeatureStatus.AVAILABLE:
            assert f.coming_soon is False, (
                f"{f.key} is AVAILABLE but still flagged coming_soon=True"
            )
        assert f.status_label, f"{f.key} has no human-readable status label"

    # the filter helper must agree with the raw registry, in order
    assert [f.key for f in get_features()] == [
        f.key for f in FEATURES if f.status != FeatureStatus.AVAILABLE
    ]
    assert [f.key for f in get_features(include_available=True)] == [
        f.key for f in FEATURES
    ]


# --------------------------------------------------------------------------- #
# 4 + 6. the page shows exactly the non-AVAILABLE entries, and every painted
#        card maps back to a real registry entry
# --------------------------------------------------------------------------- #
def test_tools_page_shows_only_non_available_registry_entries():
    _, rows = _render_tools_page()
    rendered = [name for name, _badge in rows]
    expected = _expected_non_available_names()

    assert set(rendered) == expected, (
        f"Tools page cards {sorted(rendered)} != non-AVAILABLE registry "
        f"entries {sorted(expected)}"
    )
    # count derived at runtime (never a hardcoded total)
    assert len(rendered) == len(expected)
    assert len(rendered) == len(set(rendered)), "a card was rendered twice"


def test_every_painted_card_maps_to_a_real_registry_entry():
    _, rows = _render_tools_page()
    registry = _by_name()
    for name, badge in rows:
        assert name in registry, f"painted card {name!r} has no registry entry"
        f = registry[name]
        assert badge == f.status_label, (
            f"card {name!r} badge {badge!r} != registry status_label {f.status_label!r}"
        )
        assert f.status != FeatureStatus.AVAILABLE, (
            f"{name!r} is AVAILABLE yet still painted as a coming-soon card"
        )


# --------------------------------------------------------------------------- #
# 5. the three page-backed features are absent from the Tools page
# --------------------------------------------------------------------------- #
def test_shipped_features_are_not_advertised_on_tools_page():
    _, rows = _render_tools_page()
    rendered_names = {name for name, _badge in rows}

    for key, name in SHIPPED_AS_PAGE.items():
        f = get_feature(key)
        assert f is not None, f"{key} disappeared from the registry"
        assert f.status == FeatureStatus.AVAILABLE, (
            f"{key} should be AVAILABLE (shipped as an independent page), "
            f"got {f.status!r}"
        )
        assert name not in rendered_names, (
            f"{name} ({key}) is still advertised on the Tools page"
        )


# --------------------------------------------------------------------------- #
# 7. a status change must move the card -- the actual divergence guard
# --------------------------------------------------------------------------- #
def test_page_tracks_a_status_change():
    """Flipping ``status`` must add/remove the card on the Tools page.

    Fails if ``get_features()``'s filter or ``ToolsPage._populate()`` ever stops
    honouring ``FeatureDefinition.status``. The registry is restored in a
    ``finally`` block and the restoration is itself asserted, so the guard
    leaves no side effect behind.
    """
    _, before = _render_tools_page()
    before_names = {name for name, _b in before}

    ships = next(f for f in FEATURES if f.status != FeatureStatus.AVAILABLE)
    unships = next(f for f in FEATURES if f.status == FeatureStatus.AVAILABLE)

    assert ships.name in before_names, "precondition: an unshipped feature is on the page"
    assert unships.name not in before_names, "precondition: a shipped feature is off the page"

    orig_ships, orig_unships = ships.status, unships.status
    try:
        ships.status = FeatureStatus.AVAILABLE      # ships -> must disappear
        unships.status = FeatureStatus.COMING_SOON  # un-ships -> must appear
        _, after = _render_tools_page()
        after_names = {name for name, _b in after}
    finally:
        ships.status = orig_ships
        unships.status = orig_unships

    assert ships.name not in after_names, (
        "shipping a feature did not remove its Tools-page card"
    )
    assert unships.name in after_names, (
        "un-shipping a feature did not add its Tools-page card"
    )

    _, restored = _render_tools_page()
    assert {name for name, _b in restored} == before_names, (
        "test leaked a registry mutation"
    )


def test_page_registry_comparison_is_not_vacuous():
    """Prove the equality guard above can actually fail.

    If the page matched the *unfiltered* registry, the main assertion would
    pass no matter what was painted. Assert they differ, and that the
    difference is exactly the AVAILABLE set.
    """
    _, rows = _render_tools_page()
    rendered = {name for name, _b in rows}
    unfiltered = {f.name for f in FEATURES}
    available = {f.name for f in FEATURES if f.status == FeatureStatus.AVAILABLE}

    assert available, "no AVAILABLE feature exists, so the filter is untested"
    assert rendered != unfiltered, (
        "guard is vacuous: the Tools page matches the unfiltered registry"
    )
    assert rendered == unfiltered - available, (
        "the Tools page is not exactly (registry - AVAILABLE)"
    )


def main():
    test_registry_loads()
    test_feature_keys_are_unique()
    test_status_classification_is_coherent()
    test_tools_page_shows_only_non_available_registry_entries()
    test_every_painted_card_maps_to_a_real_registry_entry()
    test_shipped_features_are_not_advertised_on_tools_page()
    test_page_tracks_a_status_change()
    test_page_registry_comparison_is_not_vacuous()
    print("\nALL FEATURE-REGISTRY REGRESSION TESTS PASSED")


if __name__ == "__main__":
    main()
