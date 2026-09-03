"""Update system configuration constants.

The manifest URL is a configurable default. In production it points at the public
HTTPS update host (Phase U2.5) so end users never depend on the internal LAN
Gitea (192.168.3.200), which remains the *internal* release source only.

Override by setting the env var `DC_UPDATE_MANIFEST_URL` (used in tests and for
self-hosting). A manifest-supplied download URL is only ever opened after it has
passed `is_allowed_download_url` (HTTPS + host allowlist), so an untrusted or
internal URL is never handed to the OS (Option B: we never auto-replace the EXE).
"""
from __future__ import annotations

import os
import urllib.parse

from .version import parse_version

PRODUCT_NAME = "DesktopCleaner"

# Default manifest endpoint. Production = public HTTPS update host. The LAN Gitea
# (192.168.3.200) is the INTERNAL release source and must never be used as an
# end-user update source. Override via env for self-hosting / tests.
UPDATE_MANIFEST_URL = os.environ.get(
    "DC_UPDATE_MANIFEST_URL",
    "https://update.ycqinnan.cn/update/latest.json",
)

# Base of the public release directory. The static host has no listing page, so a
# manifest must carry a concrete versioned download_url; this constant only
# documents the official host/prefix and is never opened unvalidated.
DOWNLOAD_PAGE_URL = "https://update.ycqinnan.cn/releases/"

# Host allowlist for manifest-supplied download URLs (Phase E.3 / E.2-R). Only
# HTTPS on exactly these hosts may be opened. Everything else (http, LAN,
# localhost, arbitrary public domains, file://, non-443 ports, embedded
# userinfo) is rejected.
ALLOWED_UPDATE_HOSTS = ("update.ycqinnan.cn",)

# Throttle: do not hit the server more than once per this interval.
UPDATE_CHECK_INTERVAL_HOURS = 24

# Network timeout (seconds). Must be short so a slow/hanging server never stalls
# the (background) check.
REQUEST_TIMEOUT_SECONDS = 8


def is_allowed_download_url(url) -> bool:
    """Return True only if `url` is HTTPS and its host is allowlisted.

    Rejects: non-HTTPS schemes, unlisted hosts, non-443 ports, embedded userinfo,
    and anything urllib cannot parse. Used before opening any manifest-supplied
    download URL (Phase E.3 acceptance: no arbitrary URL may be opened).
    """
    if not isinstance(url, str) or not url:
        return False
    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError:
        return False
    if parsed.scheme != "https":
        return False
    if parsed.username is not None or parsed.password is not None:
        return False
    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_UPDATE_HOSTS:
        return False
    try:
        port = parsed.port
    except ValueError:
        return False
    if port not in (None, 443):
        return False
    return True


def validate_manifest_basics(manifest) -> str | None:
    """Return an error reason string if a fetched manifest is unacceptable.

    Returns ``None`` when acceptable: a dict whose ``product`` is exactly
    ``PRODUCT_NAME`` and whose ``latest_version`` is a well-formed semantic
    version (so downstream ``decision.evaluate`` can never raise on it).
    """
    if not isinstance(manifest, dict):
        return "update-info-invalid"
    if manifest.get("product") != PRODUCT_NAME:
        return "update-info-invalid"
    latest = manifest.get("latest_version")
    if not isinstance(latest, str) or not latest.strip():
        return "update-info-invalid"
    try:
        parse_version(latest)
    except ValueError:
        return "update-info-invalid"
    return None
