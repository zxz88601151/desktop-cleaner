#!/usr/bin/env python3
"""Desktop Cleaner — Release Artifact Validation (read-only).

P1-3 (2026-08-31 audit): enforce a single Source of Truth for the release
artifact. This script VALIDATES only; it never renames / modifies / uploads /
deletes anything.

Naming policy (project convention, matches Gitea release v1.1.0):
    BUILD ARTIFACT NAME   = DesktopCleaner.exe        (PyInstaller spec output)
    RELEASE ARTIFACT NAME = DesktopCleaner-<VERSION>.exe   (renamed at release time)
    MANIFEST ARTIFACT     = update_manifest.json      (sha256 + download_url)
    SHA256SUMS ARTIFACT   = SHA256SUMS.txt            (sha256 + filename)
All four must agree on filename + sha256.

Usage:
    python tools/release_validate.py [--exe <path>] [--check-remote]
                                     [--manifest <path>] [--sums <path>]

    --exe <path>        Release artifact to validate. Default:
                        dist/DesktopCleaner-<VERSION>.exe
    --check-remote      Also download the remote artifact (from the release
                        page URL derived from manifest.download_url) and
                        compare its SHA-256. Requires network. Slower.
    --manifest <path>   Manifest JSON path. Default: update_manifest.json
    --sums <path>       SHA256SUMS file path. Default: SHA256SUMS.txt

Exit codes:
    0  all hard checks PASS
    1  at least one hard check FAILED
    2  no FAIL, but a required check was BLOCKED (e.g. network unavailable
       with --check-remote) — treat as "not fully verified"

Version resource inside the EXE is reported as an INFO item only (V1.1.0 EXEs
have no Win32 version resource); it never fabricates a PASS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXIT_OK = 0
EXIT_FAIL = 1
EXIT_BLOCKED = 2


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().lower()


def parse_sums(text: str) -> dict[str, str]:
    """Parse 'sha256  filename' lines -> {filename: sha256}. Tolerates CRLF."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        out[parts[1].strip()] = parts[0].strip().lower()
    return out


def load_manifest(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def http_get_status(url: str, timeout: int = 10) -> int | None:
    """Follow redirects; return final HTTP status, or None on failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ReleaseValidate"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except Exception:
        return None


def http_download_sha256(url: str, timeout: int = 30) -> tuple[str | None, int | None]:
    """Download url to a temp file; return (sha256, final_status)."""
    tmp = Path(tempfile.mkstemp(prefix="dc_relcheck_", suffix=".bin")[1])
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ReleaseValidate"})
        with urllib.request.urlopen(req, timeout=timeout) as resp, open(tmp, "wb") as f:
            for chunk in iter(lambda: resp.read(1024 * 1024), b""):
                f.write(chunk)
            status = resp.status
        return sha256_file(tmp), status
    except Exception:
        return None, None
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass


def resolve_remote_download_url(manifest: dict) -> str | None:
    """Derive the actual EXE download URL from manifest.download_url.

    release page (e.g. .../releases/latest) -> try /api/v1/.../releases/latest
    and find the DesktopCleaner-<ver>.exe asset. Direct asset URL is used as-is.
    """
    url = manifest.get("download_url")
    if not url:
        return None
    m = re.search(r"/([^/]+)/([^/]+)/releases/(?:latest|tag/[^/]+)$", url)
    if m:
        owner, repo = m.group(1), m.group(2)
        parts = urllib.parse.urlsplit(url)
        api = f"{parts.scheme}://{parts.netloc}/api/v1/repos/{owner}/{repo}/releases/latest"
        try:
            req = urllib.request.Request(api, headers={"User-Agent": "ReleaseValidate"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            assets = data.get("assets", [])
            for a in assets:
                name = a.get("name", "")
                if name.lower().startswith("desktopcleaner-") and name.lower().endswith(".exe"):
                    return a.get("browser_download_url") or a.get("url")
        except Exception:
            return None
    return None


# --------------------------------------------------------------------------- #
# checks
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--exe", help="release artifact path")
    ap.add_argument("--manifest", default=str(ROOT / "update_manifest.json"))
    ap.add_argument("--sums", default=str(ROOT / "SHA256SUMS.txt"))
    ap.add_argument("--check-remote", action="store_true",
                    help="download remote artifact and compare SHA-256")
    args = ap.parse_args()

    results: list[tuple[str, str, str]] = []  # (check, status, detail)
    failures = 0
    blocked = 0

    def report(check: str, status: str, detail: str = "") -> None:
        nonlocal failures, blocked
        results.append((check, status, detail))
        if status == "FAIL":
            failures += 1
        elif status == "BLOCKED":
            blocked += 1
        print(f"[{status:7s}] {check} {detail}")

    # ---- version --------------------------------------------------------- #
    version = None
    vfile = ROOT / "src" / "version.py"
    if vfile.exists():
        txt = vfile.read_text(encoding="utf-8")
        m = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', txt, re.M)
        version = m.group(1) if m else None
    if not version:
        report("version source", "FAIL", f"cannot parse __version__ from {vfile}")
        print("\nRESULT: FAIL (version source unreadable)")
        return EXIT_FAIL
    print(f"[INFO   ] release version (src/version.py) = {version}")

    # ---- manifest -------------------------------------------------------- #
    manifest = None
    try:
        manifest = load_manifest(Path(args.manifest))
    except Exception as exc:
        report("manifest parse", "FAIL", f"{args.manifest}: {exc}")
    mv = manifest.get("latest_version") if manifest else None

    # ---- SHA256SUMS ------------------------------------------------------ #
    sums: dict[str, str] = {}
    try:
        sums = parse_sums(Path(args.sums).read_text(encoding="utf-8"))
    except Exception as exc:
        report("SHA256SUMS parse", "FAIL", f"{args.sums}: {exc}")

    # ---- expected EXE ---------------------------------------------------- #
    expected_name = f"DesktopCleaner-{version}.exe"
    exe_path = Path(args.exe) if args.exe else ROOT / "dist" / expected_name
    exe_name = exe_path.name

    # 1. EXE existence ------------------------------------------------------ #
    if not exe_path.is_file():
        report("EXE exists", "FAIL", f"missing: {exe_path}")
    else:
        report("EXE exists", "PASS", f"{exe_path} ({exe_path.stat().st_size} B)")

    # 2. Filename consistency ----------------------------------------------- #
    sums_name = None
    for name in sums:
        if name.lower().startswith("desktopcleaner-") and name.lower().endswith(".exe"):
            sums_name = name
            break
    if manifest is None:
        pass  # manifest failure already reported
    elif expected_name not in {exe_name, sums_name}:
        report("filename consistency", "FAIL",
               f"expected={expected_name} exe={exe_name} sums={sums_name}")
    elif exe_name != sums_name:
        report("filename consistency", "FAIL",
               f"exe={exe_name} != SHA256SUMS={sums_name}")
    else:
        report("filename consistency", "PASS", f"{exe_name} == {sums_name}")

    # 3. SHA256 consistency ------------------------------------------------- #
    if exe_path.is_file():
        actual = sha256_file(exe_path)
        m_sha = (manifest or {}).get("sha256")
        s_sha = sums.get(exe_name)
        ok = bool(m_sha) and bool(s_sha) and actual == m_sha.lower() and actual == s_sha.lower()
        if ok:
            report("SHA256 consistency", "PASS", f"{actual[:16]}... (exe==manifest==sums)")
        else:
            report("SHA256 consistency", "FAIL",
                   f"exe={actual[:16]}... manifest={str(m_sha or '')[0:16]}... sums={str(s_sha or '')[0:16]}...")

    # 4. Version consistency ------------------------------------------------- #
    if manifest is not None:
        if mv == version:
            report("version consistency", "PASS", f"manifest.latest_version={mv} == src={version}")
        else:
            report("version consistency", "FAIL",
                   f"manifest.latest_version={mv} != src version={version}")
    # EXE version resource: informational only (V1.1.0 has none; never fake it)
    ver_res = False
    if exe_path.is_file():
        try:
            ver_res = b"VS_VERSION_INFO" in exe_path.read_bytes()[:2_000_000]
        except OSError:
            pass
    print(f"[INFO   ] VERSION RESOURCE: {'AVAILABLE' if ver_res else 'NOT AVAILABLE'}")

    # 5. Download artifact consistency --------------------------------------- #
    if manifest is not None:
        dl = manifest.get("download_url")
        if not dl:
            report("download artifact", "FAIL", "manifest.download_url missing")
        else:
            status = http_get_status(dl)
            if status is None:
                report("download artifact", "BLOCKED", f"network unreachable for {dl}")
            elif status != 200:
                report("download artifact", "FAIL", f"{dl} -> HTTP {status}")
            else:
                report("download artifact", "PASS", f"{dl} -> HTTP {status}")

    # 5b. remote artifact SHA-256 (optional, --check-remote) ------------------ #
    if args.check_remote and manifest is not None:
        dl = manifest.get("download_url")
        if not dl:
            pass  # already FAILed above
        else:
            rurl = resolve_remote_download_url(manifest)
            if not rurl:
                report("remote artifact", "BLOCKED", "cannot resolve remote EXE URL")
            else:
                rsha, rstatus = http_download_sha256(rurl)
                if rsha is None:
                    report("remote artifact", "BLOCKED", f"download failed ({rstatus})")
                elif exe_path.is_file() and sha256_file(exe_path) == rsha:
                    report("remote artifact", "PASS", "remote SHA-256 == local EXE")
                elif exe_path.is_file():
                    report("remote artifact", "FAIL",
                           f"remote={rsha[:16]}... != local={sha256_file(exe_path)[:16]}...")
                else:
                    report("remote artifact", "FAIL", "local EXE missing, cannot compare")

    # 6. Release metadata consistency ----------------------------------------- #
    if manifest is not None:
        rel_notes = manifest.get("release_notes")
        if not isinstance(rel_notes, list) or not rel_notes:
            report("release metadata", "FAIL", "manifest.release_notes empty/missing")
        else:
            report("release metadata", "PASS", f"{len(rel_notes)} note(s), channel={manifest.get('release_channel')}")

    # ---- summary ---------------------------------------------------------- #
    print()
    if failures:
        print(f"RESULT: FAIL ({failures} check(s) failed)")
        return EXIT_FAIL
    if blocked:
        print(f"RESULT: PASS WITH BLOCKED CHECKS ({blocked} check(s) not verified)")
        return EXIT_BLOCKED
    print("RESULT: PASS")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
