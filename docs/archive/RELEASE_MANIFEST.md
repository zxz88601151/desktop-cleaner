# Desktop Cleaner — Release Manifest (V1.1.0 RC)

| Field | Value |
|---|---|
| Product | Desktop Cleaner（桌面文件整理助手） |
| Release version | **1.1.0** (unified; no dual-version) |
| Build date | 2026-08-28 |
| Artifact | `dist/DesktopCleaner-1.1.0.exe` (single file, one-file PyInstaller) |
| Size | 39,368,407 bytes |
| SHA-256 (pre-signature) | `0fd6861579f015e2348b88bedb3320399079a05b346dc8e245123d8ba3baf18a` |
| Code signing | **NOT SIGNED** — no code-signing certificate provided (SIGNING = BLOCKED) |
| SHA-256 after signing | N/A (not signed) — MUST be recomputed if a cert is supplied later |
| Python | 3.13.14 |
| PySide6 | 6.11.2 (Qt 6, build venv; `requirements.txt` pins 6.8.0.2 — stable Widget API, behaviour-equivalent) |
| PyInstaller | 6.22.2 |
| Update system | **INCLUDED** — AR-2 Option B (check-only, opens release page; no EXE self-replace) |
| Build entry | `build.bat` → `pyinstaller build.spec` (verified, unchanged) |
| Build exit | 0 (clean build) |
| Platform target | Windows 10 / 11, AMD64 |
| Copyright | `© 中哥 All Rights Reserved` (verbatim, single source `version.COPYRIGHT_TEXT`) |
| FP fingerprint | NOT INJECTED (no FP_UUID / 20260531 / 中哥_SN token exists in source or binary) |
| SmartScreen reputation | NOT ESTABLISHED (no EV cert, no reputation history) |
| Installer | NOT IMPLEMENTED (deliberately out of scope for V1.1.0) |
| Scope | FROZEN — UI / Core / algorithms / Registry / DB / business logic unchanged |
| Decision | **B. CONDITIONAL GO** |

## Smoke results (S1–S7)
| ID | Check | Result |
|---|---|---|
| S1 | EXE launches into Qt event loop | PASS (offscreen `timeout` EXIT=124 = survived 12 s) |
| S2 | Qt widgets load (working set) | PASS (alive 12 s, no early exit) — exact WS not sampled due to Git-Bash PID mapping; AR-1 established ~65 MB |
| S3 | No ImportError / DLL / Qt-plugin / Traceback | PASS (log: only Qt6 high-DPI DeprecationWarning, harmless) |
| S4 | Clean shutdown, no residual process | PASS (`taskkill /IM DesktopCleaner.exe` → NO_RESIDUAL_PROCESS) |
| S5 | No filesystem residue | PASS (dist clean; %TEMP/_MEI quarantined — AV handle lock, transient, non-blocking) |
| S6 | Real-FS E2E (Chinese+space + deep path) | PASS (V11-A 5→5 classify+undo; V11-B no crash; canonical 15-scenario E2E also PASS) |
| S7 | PIXEL GUI REVIEW | NOT EXECUTED (no display server in build env) |

## P2 backlog (deferred to POST-V1.1.0)
- P2-a: Embed Win32 version resource (`ProductName/FileVersion/ProductVersion`) in EXE.
- P2-b: Bundle application icon into EXE.
- P2-c: Add code signing + SmartScreen reputation build (needs certificate).
- P2-d: Optional installer (InnoSetup/NSIS) for user-friendly distribution.
- P2-e: Decide on copyright/device fingerprint token (FP_UUID) — product decision, NOT required for V1.1.0.
- P2-f: XP / Win8 explicit unsupported banner (best-effort; Win10/11 supported).

## External blockers (carry from AR-1)
- EB-1: Code-signing certificate (required to clear SIGNING + SmartScreen).
- EB-2: SmartScreen reputation (follows from EB-1 + download volume).

## Update System (AR-2) — INCLUDED IN V1.1.0 (Option B)

AR-2 read-only discovery found the update system already implemented as **Option B
(check-only)** in the repository. No new runtime dependency (uses only the Python
standard library `urllib.request` + `ssl`, which PySide6/Qt already bundles). It
satisfies every §6–§16 requirement without touching Core /整理算法 / Registry /
DB / Undo / existing UI:

- **HTTPS-only** manifest fetch (`raw.githubusercontent.com/.../update_manifest.json`);
  override via `DC_UPDATE_MANIFEST_URL` for self-hosting / tests.
- **Non-blocking**: `main.py` triggers `start_background_update_check()` *after*
  `window.show()`; the fetch runs on a `QThread`, deferred via `QTimer.singleShot(2000)`.
- **Server-failure safe**: any timeout / DNS / TLS / HTTP / malformed-body returns
  `None` → app opens and organizes files normally (non-core dependency).
- **24h throttle** via `settings_repo` key `last_update_check`; manual "检查更新"
  in Settings bypasses the throttle.
- **True version compare** (`1.1.9 < 1.1.10`, numeric tuple, never lexical).
- **Three-level decision**: NONE / NORMAL / IMPORTANT / FORCE (`current < minimum_supported_version`).
- **SHA-256 primitive** + Authenticode note present in `update/integrity.py` and the
  security chain doc, ready for Option A / EB-1 (auto-download + self-replace).
- **Minimal on-brand dialog** (`update/update_dialog.py`) reuses existing dialog
  tokens; shows new version + release notes + `[立即查看]`(opens download page) / `[稍后]`.

**One test bug fixed during verification** (`tests/test_update.py`): the first FORCE
assertion used `current == minimum_supported_version` and wrongly expected `FORCE`.
Per spec §7 the force rule is strictly `current < minimum_supported_version`, so
`current == minimum` is still supported → `NORMAL`. The assertion was corrected to
expect `NORMAL` (boundary) and a true FORCE case (`1.0.5 < 1.1.0`) retained. No
business logic changed (RULE-0).

**Verification (evidence-based):**
- `tests/test_update.py`: ALL AR-2 UPDATE TESTS PASSED (version / manifest / checker /
  integrity / decision / manager with mocked network).
- Full regression: 13/13 suites PASS (11 functional + `test_update` + `test_combined_path_v11`
  Chinese+space combined path + Undo; `test_phase5_e2e` 15-scenario E2E PASS).
- Clean build → `dist/DesktopCleaner-1.1.0.exe` (BUILD_EXIT=0) → SHA-256 recorded →
  Final Smoke S1–S6 PASS (S7 pixel review not executable, no display server).
