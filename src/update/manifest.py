"""Manifest parsing / validation — pure, no Qt, no network.

A manifest is a JSON object. We require `latest_version` (well-formed); everything
else is optional and defaults sensibly. Malformed input raises ManifestError so the
caller (checker) can convert it to a silent "no update" without crashing.
"""
from __future__ import annotations

import json

from .version import parse_version


class ManifestError(Exception):
    """Raised when the manifest text is not a valid, well-formed manifest."""


def parse_manifest(text: str) -> dict:
    """Parse manifest JSON text into a normalized dict.

    Raises ManifestError on: not JSON, not an object, missing/invalid
    `latest_version`, or invalid `minimum_supported_version`.
    """
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ManifestError(f"malformed JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ManifestError("manifest root must be a JSON object")

    latest = data.get("latest_version")
    if not isinstance(latest, str) or not latest.strip():
        raise ManifestError("missing or invalid 'latest_version'")
    try:
        parse_version(latest)
    except ValueError as exc:
        raise ManifestError(f"invalid 'latest_version': {latest!r}") from exc

    minimum = data.get("minimum_supported_version")
    if minimum is not None:
        if not isinstance(minimum, str) or not minimum.strip():
            raise ManifestError("invalid 'minimum_supported_version'")
        try:
            parse_version(minimum)
        except ValueError as exc:
            raise ManifestError(
                f"invalid 'minimum_supported_version': {minimum!r}"
            ) from exc

    notes = data.get("release_notes")
    if notes is not None and not isinstance(notes, list):
        notes = [str(notes)]

    return {
        "schema_version": data.get("schema_version", 1),
        "product": data.get("product"),
        "latest_version": latest.strip(),
        "minimum_supported_version": minimum.strip() if minimum else None,
        "release_channel": data.get("release_channel", "stable"),
        "download_url": data.get("download_url"),
        "sha256": data.get("sha256"),
        "release_notes": notes or [],
        "published_at": data.get("published_at"),
    }
