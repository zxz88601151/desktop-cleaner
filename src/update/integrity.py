"""Integrity primitives — pure, no Qt, no network.

These are the building blocks for Option A (auto-download + verify + replace). They
are implemented and tested now so the security chain (HTTPS -> SHA-256 ->
Authenticode) is ready, even though V1.1.0 ships Option B (check-only) and therefore
does not download or replace the EXE. SHA-256 alone is NOT sufficient trust; the
Authenticode / publisher step is handled at install time (POST-V1.1.0, EB-1).
"""
from __future__ import annotations

import hashlib


def sha256_bytes(data: bytes) -> str:
    """Return lowercase hex SHA-256 of `data`."""
    return hashlib.sha256(data).hexdigest().lower()


def verify_sha256(expected: str | None, data: bytes) -> bool:
    """Return True only if `expected` is present and matches SHA-256 of `data`.

    Missing/empty expected hash -> False (never trust an unverified payload).
    Comparison is case-insensitive and tolerant of surrounding whitespace.
    """
    if not expected:
        return False
    return sha256_bytes(data) == expected.strip().lower()
