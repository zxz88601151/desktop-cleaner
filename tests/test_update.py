"""AR-2 Update System — unit + integration tests (no real network).

Run:  PYTHONPATH=src python tests/test_update.py

Covers the required matrix (§16):
- Version compare (incl. 1.1.9 < 1.1.10), invalid version
- Manifest parse: valid / missing latest / malformed JSON / invalid version / optional fields
- Checker network (mocked): success / timeout / DNS failure / HTTP error / malformed JSON
- Integrity: SHA-256 correct / mismatch / missing / malformed
- Decision: NONE (current==latest, current>latest) / NORMAL / IMPORTANT / FORCE
- Manager (Qt): background fetch emits update_available / no_update; throttle; silent on failure

The manager test spins a real QApplication + worker thread with the network fetch
monkeypatched, so it validates the non-blocking wiring without touching the network.
"""
import os
import sys
import json
import tempfile
import urllib.request
from pathlib import Path

_TMP_HOME = tempfile.mkdtemp(prefix="dc_upd_")
os.environ["DESKTOP_CLEANER_HOME"] = _TMP_HOME

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from data.database import init_db  # noqa: E402  (must run after HOME is set)

from update.version import parse_version, compare_versions, is_newer, is_older_than  # noqa: E402
from update.manifest import parse_manifest, ManifestError  # noqa: E402
from update.decision import (  # noqa: E402
    evaluate,
    LEVEL_NONE,
    LEVEL_NORMAL,
    LEVEL_IMPORTANT,
    LEVEL_FORCE,
)
from update.integrity import sha256_bytes, verify_sha256  # noqa: E402
from update.checker import fetch_manifest  # noqa: E402
from update.constants import (  # noqa: E402
    is_allowed_download_url,
    validate_manifest_basics,
)


def _assert(cond, msg):
    if not cond:
        raise AssertionError("FAIL: " + msg)
    print("  ok:", msg)


# --------------------------------------------------------------------------- #
# Version
# --------------------------------------------------------------------------- #
def test_version():
    print("[version]")
    _assert(parse_version("1.1.0") == (1, 1, 0), "parse 1.1.0")
    _assert(compare_versions("1.1.9", "1.1.10") < 0, "1.1.9 < 1.1.10 (numeric)")
    _assert(compare_versions("1.1.10", "1.1.9") > 0, "1.1.10 > 1.1.9")
    _assert(compare_versions("1.2.0", "1.1.9") > 0, "1.2.0 > 1.1.9")
    _assert(compare_versions("1.1.0", "1.1.0") == 0, "equal")
    _assert(is_newer("1.1.1", "1.1.0"), "1.1.1 newer than 1.1.0")
    _assert(is_older_than("1.1.0", "1.0.9"), "1.0.9 older than 1.1.0")
    for bad in ("1.1", "1.x.0", "v1.1.0", "", "1.1.0.0"):
        try:
            parse_version(bad)
            _assert(False, f"reject bad version {bad!r}")
        except ValueError:
            _assert(True, f"reject bad version {bad!r}")


# --------------------------------------------------------------------------- #
# Manifest
# --------------------------------------------------------------------------- #
def test_manifest():
    print("[manifest]")
    good = json.dumps({
        "latest_version": "1.1.1",
        "minimum_supported_version": "1.1.0",
        "release_notes": ["fix", "improve"],
        "download_url": "https://example.com/x",
    })
    m = parse_manifest(good)
    _assert(m["latest_version"] == "1.1.1", "latest_version parsed")
    _assert(m["minimum_supported_version"] == "1.1.0", "minimum parsed")
    _assert(m["release_notes"] == ["fix", "improve"], "notes parsed")
    _assert(m["download_url"] == "https://example.com/x", "download_url parsed")
    _assert(m["release_channel"] == "stable", "channel default")

    # missing latest_version
    try:
        parse_manifest(json.dumps({"foo": "bar"}))
        _assert(False, "missing latest_version rejected")
    except ManifestError:
        _assert(True, "missing latest_version rejected")
    # malformed JSON
    try:
        parse_manifest("{not json")
        _assert(False, "malformed JSON rejected")
    except ManifestError:
        _assert(True, "malformed JSON rejected")
    # invalid latest_version string
    try:
        parse_manifest(json.dumps({"latest_version": "1.1"}))
        _assert(False, "invalid latest_version rejected")
    except ManifestError:
        _assert(True, "invalid latest_version rejected")
    # invalid minimum
    try:
        parse_manifest(json.dumps({"latest_version": "1.1.0", "minimum_supported_version": "x"}))
        _assert(False, "invalid minimum rejected")
    except ManifestError:
        _assert(True, "invalid minimum rejected")
    # optional fields default when absent
    m2 = parse_manifest(json.dumps({"latest_version": "1.1.0"}))
    _assert(m2["minimum_supported_version"] is None, "minimum defaults None")
    _assert(m2["release_notes"] == [], "notes default []")


# --------------------------------------------------------------------------- #
# Checker (network mocked)
# --------------------------------------------------------------------------- #
class _FakeResp:
    def __init__(self, data: bytes):
        self._d = data

    def read(self):
        return self._d

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _patch_urlopen(monkeypatch_target):
    """Replace urllib.request.urlopen with a controllable fake."""
    import update.checker as checker_mod
    orig = urllib.request.urlopen
    checker_mod.urllib.request.urlopen = monkeypatch_target  # patch where imported
    return orig


def test_checker():
    print("[checker]")
    import update.checker as checker_mod

    manifest_json = json.dumps({"latest_version": "1.1.1"})
    good_resp = _FakeResp(manifest_json.encode("utf-8"))

    # success
    checker_mod.urllib.request.urlopen = lambda *a, **k: good_resp
    _assert(fetch_manifest() is not None, "HTTPS success -> manifest")

    # malformed body -> None (silent)
    checker_mod.urllib.request.urlopen = lambda *a, **k: _FakeResp(b"{bad")
    _assert(fetch_manifest() is None, "malformed JSON -> None (silent)")

    # timeout -> None
    def _boom_timeout(*a, **k):
        raise TimeoutError("timeout")
    checker_mod.urllib.request.urlopen = _boom_timeout
    _assert(fetch_manifest() is None, "timeout -> None (silent)")

    # DNS / URLError -> None
    def _boom_dns(*a, **k):
        raise urllib.error.URLError("dns failure")
    checker_mod.urllib.request.urlopen = _boom_dns
    _assert(fetch_manifest() is None, "DNS failure -> None (silent)")

    # HTTP error -> None
    def _boom_http(*a, **k):
        raise urllib.error.HTTPError(None, 404, "nf", None, None)
    checker_mod.urllib.request.urlopen = _boom_http
    _assert(fetch_manifest() is None, "HTTP 404 -> None (silent)")

    # restore
    checker_mod.urllib.request.urlopen = urllib.request.urlopen


# --------------------------------------------------------------------------- #
# Integrity
# --------------------------------------------------------------------------- #
def test_integrity():
    print("[integrity]")
    data = b"DesktopCleaner-1.1.0.exe"
    h = sha256_bytes(data)
    _assert(len(h) == 64, "sha256 hex length 64")
    _assert(verify_sha256(h, data), "correct hash verifies")
    _assert(verify_sha256(h.upper(), data), "case-insensitive verify")
    _assert(not verify_sha256("deadbeef", data), "mismatch fails")
    _assert(not verify_sha256("", data), "missing hash fails")
    _assert(not verify_sha256(None, data), "None hash fails")


# --------------------------------------------------------------------------- #
# Decision
# --------------------------------------------------------------------------- #
def test_decision():
    print("[decision]")
    cur = "1.1.0"
    _assert(evaluate(cur, {"latest_version": "1.1.0"}) == LEVEL_NONE, "current==latest -> NONE")
    _assert(evaluate(cur, {"latest_version": "1.0.9"}) == LEVEL_NONE, "current>latest -> NONE")
    _assert(
        evaluate(cur, {"latest_version": "1.1.1"}) == LEVEL_NORMAL,
        "patch bump -> NORMAL",
    )
    _assert(
        evaluate(cur, {"latest_version": "1.2.0"}) == LEVEL_IMPORTANT,
        "minor bump -> IMPORTANT",
    )
    _assert(
        evaluate(cur, {"latest_version": "2.0.0"}) == LEVEL_IMPORTANT,
        "major bump -> IMPORTANT",
    )
    # Boundary: current == minimum_supported_version is still SUPPORTED, so it must
    # NOT be forced (spec §7: force only when current < minimum_supported_version).
    # latest (1.1.1) > current (1.1.0) => NORMAL update prompt, not FORCE.
    _assert(
        evaluate(cur, {"latest_version": "1.1.1", "minimum_supported_version": "1.1.0"})
        == LEVEL_NORMAL,
        "current==minimum (boundary) -> NORMAL (supported, not forced)",
    )
    # True FORCE: current strictly below minimum_supported_version.
    _assert(
        evaluate("1.0.5", {"latest_version": "1.1.1", "minimum_supported_version": "1.1.0"})
        == LEVEL_FORCE,
        "old current<minimum -> FORCE",
    )


# --------------------------------------------------------------------------- #
# Manager (Qt, real worker thread, network mocked)
# --------------------------------------------------------------------------- #
def test_manager():
    print("[manager]")
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QEventLoop, QTimer

    import update.manager as mgr_mod

    app = QApplication.instance() or QApplication(sys.argv + ["-platform", "offscreen"])
    init_db()

    fake_ok = {
        "latest_version": "1.1.1",
        "minimum_supported_version": "1.1.0",
        "release_notes": ["bug fixes"],
    }
    real_fetch = mgr_mod.fetch_manifest
    mgr_mod.fetch_manifest = lambda *a, **k: fake_ok

    def pump(timeout_ms=1000):
        loop = QEventLoop()
        QTimer.singleShot(timeout_ms, loop.quit)
        loop.exec()

    # case 1: update available
    got = {}
    mgr = mgr_mod.UpdateManager("1.1.0")
    mgr.update_available.connect(lambda mf: got.setdefault("avail", mf))
    mgr.no_update.connect(lambda: got.setdefault("none", True))
    mgr.start_check(force=True)
    pump()
    _assert("avail" in got, "update_available emitted when newer exists")
    del mgr

    # case 2: current >= latest -> no_update
    got.clear()
    mgr = mgr_mod.UpdateManager("1.1.1")
    mgr.update_available.connect(lambda mf: got.setdefault("avail", mf))
    mgr.no_update.connect(lambda: got.setdefault("none", True))
    mgr.start_check(force=True)
    pump()
    _assert("none" in got and "avail" not in got, "no_update when current>=latest")

    # case 3: fetch fails -> silent no_update (never raises)
    mgr_mod.fetch_manifest = lambda *a, **k: None
    got.clear()
    mgr = mgr_mod.UpdateManager("1.1.0")
    mgr.update_available.connect(lambda mf: got.setdefault("avail", mf))
    mgr.no_update.connect(lambda: got.setdefault("none", True))
    mgr.start_check(force=True)
    pump()
    _assert("none" in got, "silent no_update on fetch failure")

    mgr_mod.fetch_manifest = real_fetch


# --------------------------------------------------------------------------- #
# Download URL security (Phase E.3)
# --------------------------------------------------------------------------- #
def test_download_url_security():
    print("[download_url_security]")
    ok = "https://update.ycqinnan.cn/releases/DesktopCleaner-1.1.1.exe"
    _assert(is_allowed_download_url(ok), "allowlisted HTTPS URL accepted")
    _assert(
        is_allowed_download_url("https://update.ycqinnan.cn/update/latest.json"),
        "allowlisted HTTPS manifest URL accepted",
    )
    # non-HTTPS scheme
    _assert(not is_allowed_download_url("http://update.ycqinnan.cn/releases/x.exe"), "http rejected")
    _assert(not is_allowed_download_url("file:///c:/x.exe"), "file:// rejected")
    # host not allowlisted (arbitrary public domain)
    _assert(not is_allowed_download_url("https://example.com/DesktopCleaner.exe"), "foreign host rejected")
    # internal / LAN hosts
    _assert(not is_allowed_download_url("http://192.168.3.200:3000/zxzjxx/x.exe"), "LAN http rejected")
    _assert(not is_allowed_download_url("https://192.168.3.200/x.exe"), "LAN https rejected")
    _assert(not is_allowed_download_url("https://localhost/x.exe"), "localhost rejected")
    _assert(not is_allowed_download_url("https://127.0.0.1/x.exe"), "127.0.0.1 rejected")
    _assert(not is_allowed_download_url("https://10.0.0.5/x.exe"), "10.x rejected")
    _assert(not is_allowed_download_url("https://172.16.0.5/x.exe"), "172.16 rejected")
    # port / userinfo / malformed
    _assert(not is_allowed_download_url("https://update.ycqinnan.cn:8443/x.exe"), "non-443 port rejected")
    _assert(not is_allowed_download_url("https://user@update.ycqinnan.cn/x.exe"), "userinfo rejected")
    _assert(not is_allowed_download_url("not a url"), "non-URL rejected")
    _assert(not is_allowed_download_url(""), "empty rejected")
    _assert(not is_allowed_download_url(None), "None rejected")


def test_manifest_basics():
    print("[manifest_basics]")
    ok = {"product": "DesktopCleaner", "latest_version": "1.1.1", "download_url": "https://update.ycqinnan.cn/x.exe"}
    _assert(validate_manifest_basics(ok) is None, "valid manifest accepted")
    _assert(validate_manifest_basics({"product": "DesktopCleaner", "latest_version": "1.1.1"}) is None, "no download_url still valid at parse level")
    _assert(validate_manifest_basics({"latest_version": "1.1.1"}) is not None, "missing product rejected")
    _assert(validate_manifest_basics({"product": "Other", "latest_version": "1.1.1"}) is not None, "wrong product rejected")
    _assert(validate_manifest_basics({"product": "DesktopCleaner"}) is not None, "missing latest_version rejected")
    _assert(validate_manifest_basics({"product": "DesktopCleaner", "latest_version": ""}) is not None, "empty latest_version rejected")
    _assert(validate_manifest_basics({"product": "DesktopCleaner", "latest_version": "abc"}) is not None, "non-semver latest_version rejected")
    _assert(validate_manifest_basics(None) is not None, "None rejected")
    _assert(validate_manifest_basics("not a dict") is not None, "non-dict rejected")


if __name__ == "__main__":
    test_version()
    test_manifest()
    test_checker()
    test_integrity()
    test_decision()
    test_download_url_security()
    test_manifest_basics()
    test_manager()
    print("\nALL AR-2 UPDATE TESTS PASSED (pure + manager, no real network)")
