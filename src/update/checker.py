"""HTTPS manifest fetch — pure, standard-library only (zero new dependencies).

This module is intentionally free of any Qt import so it can be unit-tested without
a QApplication and run inside a worker thread. ANY failure (timeout, DNS, TLS, HTTP
status, malformed body) returns ``None`` — the update check is a NON-CORE dependency
and must never block or crash the application.
"""
from __future__ import annotations

import urllib.request

from .constants import PRODUCT_NAME, REQUEST_TIMEOUT_SECONDS, UPDATE_MANIFEST_URL
from .manifest import ManifestError, parse_manifest


def fetch_manifest(
    url: str | None = None,
    timeout: int = REQUEST_TIMEOUT_SECONDS,
) -> dict | None:
    """Fetch and parse the update manifest.

    Returns the normalized manifest dict, or ``None`` on any network/parse failure.
    The caller treats ``None`` as "no update / check skipped" and stays silent.
    """
    target = url or UPDATE_MANIFEST_URL
    req = urllib.request.Request(
        target,
        headers={"User-Agent": f"{PRODUCT_NAME}-UpdateCheck"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
        return parse_manifest(raw)
    except Exception:
        # timeout / DNS / TLS / HTTP error / malformed JSON -> silent, non-blocking
        return None
