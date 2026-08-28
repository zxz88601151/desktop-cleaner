"""Desktop Cleaner — in-app update system (Option B: check-only).

Design constraints (AR-2, RULE-0):
- Must NOT block application startup.
- Must NOT depend on the update server for the app to open (server down / offline
  => the app still launches and organizes files normally).
- Zero new runtime dependencies: uses only the Python standard library for the
  network fetch (urllib.request + ssl), which PySide6/Qt already bundles.
- Pure logic modules (version / manifest / checker / decision / integrity) have no
  Qt import so they are unit-testable without a QApplication.
- Option A (auto-download + self-replace EXE + Authenticode verification) is DEFERRED
  to POST-V1.1.0 / EB-1 because it requires a code-signing certificate that is not
  available yet. The integrity primitive lives here so the security chain is ready.
"""
from __future__ import annotations
