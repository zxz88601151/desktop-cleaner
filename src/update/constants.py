"""Update system configuration constants.

The manifest URL is a configurable default. It points at a versioned raw JSON
file committed to the project repository's `main` branch; the shipped EXE checks
it over HTTPS. If the host is unreachable / the file does not exist yet, the check
fails silently and the app opens normally (non-core dependency).

Override by setting the env var `DC_UPDATE_MANIFEST_URL` (used in tests and for
self-hosting). The download page is where the user is sent when an update exists
(Option B: we never auto-replace the EXE).
"""
from __future__ import annotations

import os

PRODUCT_NAME = "DesktopCleaner"

# Default manifest endpoint. Override via env for self-hosting / tests.
# P1-1 (2026-08-31 audit): the formal release channel is the LAN Gitea instance
# (192.168.3.200), not GitHub — GitHub was 404/unreachable while Gitea serves the
# manifest with HTTP 200. HTTPS is unavailable on the LAN Gitea (plain HTTP).
UPDATE_MANIFEST_URL = os.environ.get(
    "DC_UPDATE_MANIFEST_URL",
    "http://192.168.3.200:3000/zxzjxx/desktop-cleaner/raw/branch/main/update_manifest.json",
)

# Where the user lands when an update is available (Option B). Gitea resolves
# /releases/latest to the newest published release automatically.
DOWNLOAD_PAGE_URL = "http://192.168.3.200:3000/zxzjxx/desktop-cleaner/releases/latest"

# Throttle: do not hit the server more than once per this interval.
UPDATE_CHECK_INTERVAL_HOURS = 24

# Network timeout (seconds). Must be short so a slow/hanging server never stalls
# the (background) check.
REQUEST_TIMEOUT_SECONDS = 8
