"""Phase E.3 — About page "检查更新" state machine (no real network).

Covers the acceptance matrix:
- IDLE / CHECKING / UP_TO_DATE / UPDATE_AVAILABLE / ERROR
- fail-closed semantics: network failure / invalid JSON / missing latest_version /
  wrong product / unsafe download_url must NEVER surface as "up to date"
- HTTPS + host allowlist enforcement before any download action
- no repeat click while a check is running
- UpdateDialog refuses to offer an unsafe download URL

The network fetch is monkeypatched (`ui.about.fetch_manifest`); nothing touches the
public endpoint (which correctly stays 404 until the release phase).
"""
import os
import sys
import tempfile
from pathlib import Path

_TMP_HOME = tempfile.mkdtemp(prefix="dc_about_")
os.environ["DESKTOP_CLEANER_HOME"] = _TMP_HOME

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtCore import QEventLoop, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from data.database import init_db  # noqa: E402

import ui.about as about_mod  # noqa: E402
from ui.about import AboutDialog  # noqa: E402
from update.update_dialog import UpdateDialog  # noqa: E402
from version import __version__  # noqa: E402

app = QApplication.instance() or QApplication(["-platform", "offscreen"])
init_db()


def _pump(ms=600):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def _set_fetch(manifest):
    about_mod.fetch_manifest = lambda *a, **k: manifest


def _check(manifest):
    """Build dialog, feed the manifest through the worker, pump, return dialog."""
    dlg = AboutDialog()
    _set_fetch(manifest)
    dlg._on_check_update()
    _pump()
    return dlg


def _text(dlg):
    return dlg._update_status.text()


# --------------------------------------------------------------------------- #
def test_idle_default():
    dlg = AboutDialog()
    assert dlg._check_btn.text() == "检查更新"
    assert dlg._check_btn.isEnabled()
    assert _text(dlg) == ""
    assert dlg._download_btn.isHidden()
    dlg.close()


def test_scenario_a_already_latest():
    dlg = _check({"product": "DesktopCleaner", "latest_version": __version__})
    assert "当前已是最新版本" in _text(dlg)
    assert dlg._download_btn.isHidden()
    dlg.close()


def test_scenario_c_older_manifest():
    # server latest < current -> UP_TO_DATE (not an error, not "new version")
    dlg = _check({"product": "DesktopCleaner", "latest_version": "0.9.0"})
    assert "当前已是最新版本" in _text(dlg)
    assert dlg._download_btn.isHidden()
    dlg.close()


def test_scenario_b_new_version():
    dlg = _check({
        "product": "DesktopCleaner",
        "latest_version": "9.9.9",
        "download_url": "https://update.ycqinnan.cn/releases/DesktopCleaner-9.9.9.exe",
    })
    assert "发现新版本" in _text(dlg)
    assert not dlg._download_btn.isHidden()
    dlg.close()


def test_scenario_d_network_failure():
    # MUST be ERROR, NEVER up-to-date
    dlg = _check(None)
    assert "检查更新失败" in _text(dlg)
    assert "最新版本" not in _text(dlg)
    assert dlg._download_btn.isHidden()
    dlg.close()


def test_scenario_e_invalid_json():
    # fetch_manifest already maps malformed JSON -> None -> ERROR
    dlg = _check(None)
    assert "检查更新失败" in _text(dlg)
    dlg.close()


def test_scenario_f_missing_latest_version():
    dlg = _check({"product": "DesktopCleaner"})
    assert "检查更新失败" in _text(dlg)
    dlg.close()


def test_invalid_latest_version():
    # non-semver latest_version must be fail-closed (never crash, never up-to-date)
    dlg = _check({"product": "DesktopCleaner", "latest_version": "not-a-version"})
    assert "检查更新失败" in _text(dlg)
    dlg.close()


def test_wrong_or_missing_product():
    for manifest in (
        {"latest_version": "9.9.9"},
        {"product": "Other", "latest_version": "9.9.9"},
        "not-a-dict",
    ):
        dlg = _check(manifest)
        assert "检查更新失败" in _text(dlg), manifest
        dlg.close()


def test_scenario_g_invalid_download_url():
    # update exists but unsafe download URL -> ERROR, never offered
    for bad in (
        "http://192.168.3.200:3000/zxzjxx/x.exe",
        "https://example.com/DesktopCleaner.exe",
        "https://update.ycqinnan.cn:8443/x.exe",
        "http://update.ycqinnan.cn/x.exe",
        "",
    ):
        dlg = _check({"product": "DesktopCleaner", "latest_version": "9.9.9", "download_url": bad})
        assert "检查更新失败" in _text(dlg), bad
        assert dlg._download_btn.isHidden(), bad
        dlg.close()


def test_scenario_h_unauthorized_host_rejected():
    dlg = _check({"product": "DesktopCleaner", "latest_version": "9.9.9",
                  "download_url": "https://example.com/DesktopCleaner.exe"})
    assert "检查更新失败" in _text(dlg)
    assert dlg._download_btn.isHidden()
    dlg.close()


def test_no_repeat_click_while_checking():
    dlg = AboutDialog()
    _set_fetch({"product": "DesktopCleaner", "latest_version": __version__})
    dlg._on_check_update()
    assert dlg._checking is True
    assert not dlg._check_btn.isEnabled()
    dlg._on_check_update()  # ignored
    assert dlg._checking is True
    _pump()
    assert dlg._checking is False
    assert dlg._check_btn.isEnabled()
    dlg.close()


def test_download_opens_only_validated_url():
    recorded = []
    orig = about_mod.QDesktopServices.openUrl
    about_mod.QDesktopServices.openUrl = lambda url: recorded.append(str(url.toString()))
    try:
        dlg = AboutDialog()
        # invalid -> _on_download must do nothing
        dlg._latest_manifest = {
            "product": "DesktopCleaner",
            "latest_version": "9.9.9",
            "download_url": "http://192.168.3.200:3000/x.exe",
        }
        dlg._on_download()
        assert recorded == [], "invalid URL must not be opened"
        # valid -> opened
        valid = "https://update.ycqinnan.cn/releases/DesktopCleaner-9.9.9.exe"
        dlg._latest_manifest = {
            "product": "DesktopCleaner",
            "latest_version": "9.9.9",
            "download_url": valid,
        }
        dlg._on_download()
        assert recorded == [valid], "validated URL should be opened"
        dlg.close()
    finally:
        about_mod.QDesktopServices.openUrl = orig


def test_update_dialog_rejects_unsafe_url():
    manifest = {
        "product": "DesktopCleaner",
        "latest_version": "9.9.9",
        "download_url": "http://192.168.3.200:3000/zxzjxx/x.exe",
    }
    dlg = UpdateDialog(manifest, __version__)
    # No "立即查看" open button may be offered for an unsafe URL.
    from PySide6.QtWidgets import QPushButton

    buttons = [b for b in dlg.findChildren(QPushButton)]
    assert all(b.text() != "立即查看" for b in buttons), "unsafe URL must not offer 立即查看"
    dlg.close()


def test_update_dialog_allows_safe_url():
    from PySide6.QtWidgets import QPushButton

    manifest = {
        "product": "DesktopCleaner",
        "latest_version": "9.9.9",
        "download_url": "https://update.ycqinnan.cn/releases/DesktopCleaner-9.9.9.exe",
    }
    dlg = UpdateDialog(manifest, __version__)
    buttons = [b.text() for b in dlg.findChildren(QPushButton)]
    assert "立即查看" in buttons, "safe URL should offer 立即查看"
    dlg.close()


if __name__ == "__main__":
    test_idle_default()
    test_scenario_a_already_latest()
    test_scenario_c_older_manifest()
    test_scenario_b_new_version()
    test_scenario_d_network_failure()
    test_scenario_e_invalid_json()
    test_scenario_f_missing_latest_version()
    test_invalid_latest_version()
    test_wrong_or_missing_product()
    test_scenario_g_invalid_download_url()
    test_scenario_h_unauthorized_host_rejected()
    test_no_repeat_click_while_checking()
    test_download_opens_only_validated_url()
    test_update_dialog_rejects_unsafe_url()
    test_update_dialog_allows_safe_url()
    print("\nALL PHASE E.3 ABOUT UPDATE TESTS PASSED (no real network)")
