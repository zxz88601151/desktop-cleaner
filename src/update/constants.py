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

# Default manifest endpoint (HTTPS). Override via env for self-hosting / tests.
UPDATE_MANIFEST_URL = os.environ.get(
    "DC_UPDATE_MANIFEST_URL",
    "https://raw.githubusercontent.com/zxz88601151/desktop-cleaner/main/update_manifest.json",
)

# Where the user lands when an update is available (Option B). GitHub resolves
# /releases/latest to the newest published release automatically.
DOWNLOAD_PAGE_URL = "https://github.com/zxz88601151/desktop-cleaner/releases/latest"

# Throttle: do not hit the server more than once per this interval.
UPDATE_CHECK_INTERVAL_HOURS = 24

# Network timeout (seconds). Must be short so a slow/hanging server never stalls
# the (background) check.
REQUEST_TIMEOUT_SECONDS = 8
