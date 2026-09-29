"""Report export (V1.2-A, feature 3).

Turns an :class:`~core.analysis.AnalysisResult` into a portable report and
writes it as **JSON** or **CSV**. Qt-free and pure: it only *reads* the result
object and writes the one file the caller asked for.

Design rules
------------
- **Stable field names, explicit units.** Byte counts are always suffixed
  ``_bytes``; timestamps are always suffixed ``_epoch`` (Unix seconds, UTC
  based). No locale-dependent formatting leaks into the data.
- **No UI text as data.** Categories are exported by their stable key
  (``images`` / ``documents`` / ...). A separate ``category_labels`` block maps
  keys to Chinese labels purely as a *display aid* — it is never the identity
  of a record.
- **Provenance is recorded.** Every report carries ``schema``,
  ``generated_at`` (+ epoch), ``app_version``, ``rules_version`` (a content
  fingerprint of the rule set) and ``rules_count``, so two reports can be
  compared and a report can always be traced back to the rules that made it.
- **UTF-8 throughout.** JSON is written as plain UTF-8. CSV is written as
  UTF-8 **with BOM** so Microsoft Excel on a Chinese Windows opens it without
  mojibake; the bytes are still valid UTF-8 and any strict reader can consume
  them.
- **The CSV is one strict RFC-4180 table.** Heterogeneous sections share a
  single header and a ``section`` column rather than being stacked into
  pseudo-sections, so the file stays machine-parseable.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence

from .analysis import AnalysisResult
from .rules import CATEGORY_NAMES, DEFAULT_RULES, rules_fingerprint

# Bump when the shape of the exported document changes.
REPORT_SCHEMA = "desktop-cleaner.report.v1"

# One header for every section (see module docstring).
CSV_COLUMNS: Sequence[str] = (
    "section",
    "item",
    "count",
    "size_bytes",
    "folder_count",
    "path",
    "mtime_epoch",
    "value",
)

#: Sections emitted in the CSV, in order.
CSV_SECTIONS: Sequence[str] = (
    "summary",
    "category",
    "extension",
    "largest_file",
    "largest_folder",
    "recent_file",
    "empty_folder",
)


def build_report(
    result: AnalysisResult,
    *,
    app_version: str = "unknown",
    rules: Optional[Dict[str, str]] = None,
    generated_at: Optional[datetime] = None,
) -> dict:
    """Assemble the full report document (a plain, JSON-safe ``dict``)."""
    rules = DEFAULT_RULES if rules is None else rules
    now = generated_at or datetime.now().astimezone()
    return {
        "schema": REPORT_SCHEMA,
        "generated_at": now.isoformat(timespec="seconds"),
        "generated_at_epoch": int(now.timestamp()),
        "app_version": app_version,
        "rules_version": rules_fingerprint(rules),
        "rules_count": len(rules),
        "analysis": result.to_dict(),
        # Display aid only: keys are the data, labels are convenience.
        "category_labels": dict(CATEGORY_NAMES),
        "notes": {
            "size_unit": "bytes",
            "time_unit": "unix_epoch_seconds",
            "scope": "read-only analysis; no file was created, moved or deleted",
            "empty_folder_semantics": (
                "a folder whose whole subtree contains no file; hidden / system / "
                "junction / symlink paths are excluded"
            ),
            "category_key_semantics": (
                "categories are identified by stable keys; see category_labels "
                "for the display mapping"
            ),
            "csv_encoding": "UTF-8 with BOM",
        },
    }


# --------------------------------------------------------------------------- #
# CSV
# --------------------------------------------------------------------------- #
def report_rows(report: dict) -> Iterator[List]:
    """Yield CSV rows (header first) for *report*.

    Row semantics per section (empty cells where a column does not apply):

    - ``summary``        item = metric name; value holds the metric
                         (``total_size_bytes`` / ``file_count`` / ...)
    - ``category``       item = stable category key; count / size_bytes
    - ``extension``      item = extension (or ``(none)``); count / size_bytes
    - ``largest_file``   item = rank; size_bytes; path; mtime_epoch
    - ``largest_folder`` item = rank; count = direct files; size_bytes = subtree;
                         folder_count = direct subfolders; path
    - ``recent_file``    item = rank; size_bytes; path; mtime_epoch
    - ``empty_folder``   item = rank; path
    """
    a = report["analysis"]

    yield list(CSV_COLUMNS)

    # summary -------------------------------------------------------------- #
    for metric, value in (
        ("total_size_bytes", a["total_size_bytes"]),
        ("file_count", a["file_count"]),
        ("folder_count", a["folder_count"]),
        ("skipped", a["skipped"]),
        ("duration_ms", a["duration_ms"]),
        ("schema", report["schema"]),
        ("app_version", report["app_version"]),
        ("rules_version", report["rules_version"]),
        ("rules_count", report["rules_count"]),
        ("generated_at", report["generated_at"]),
        ("generated_at_epoch", report["generated_at_epoch"]),
    ):
        yield ["summary", metric, "", "", "", "", "", value]

    for entry in a["by_category"]:
        yield ["category", entry["category"], entry["files"],
               entry["size_bytes"], "", "", "", ""]

    for entry in a["by_extension"]:
        yield ["extension", entry["extension"], entry["files"],
               entry["size_bytes"], "", "", "", ""]

    for i, f in enumerate(a["largest_files"], 1):
        yield ["largest_file", i, "", f["size"], "", f["path"], f["mtime"], ""]

    for i, d in enumerate(a["largest_folders"], 1):
        yield ["largest_folder", i, d["file_count"], d["total_size"],
               d["folder_count"], d["path"], "", ""]

    for i, f in enumerate(a["recent_files"], 1):
        yield ["recent_file", i, "", f["size"], "", f["path"], f["mtime"], ""]

    for i, p in enumerate(a["empty_folders"], 1):
        yield ["empty_folder", i, "", "", "", p, "", ""]


def write_csv(report: dict, path: Path) -> Path:
    """Write *report* as one RFC-4180 CSV (UTF-8 with BOM). Returns the path."""
    path = Path(path)
    # newline="" is required by the csv module; utf-8-sig = UTF-8 + BOM so that
    # Excel on a Chinese Windows renders the content correctly.
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\r\n")
        writer.writerows(report_rows(report))
    return path


# --------------------------------------------------------------------------- #
# JSON
# --------------------------------------------------------------------------- #
def write_json(report: dict, path: Path) -> Path:
    """Write *report* as pretty UTF-8 JSON. Returns the path."""
    path = Path(path)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return path


# --------------------------------------------------------------------------- #
# dispatcher
# --------------------------------------------------------------------------- #
_SUFFIX_WRITERS = {
    ".json": write_json,
    ".csv": write_csv,
}


def supported_formats() -> List[str]:
    """Suffixes :func:`export` accepts (for a file-dialog filter)."""
    return sorted(_SUFFIX_WRITERS)


def export(
    result: AnalysisResult,
    path,
    *,
    app_version: str = "unknown",
    rules: Optional[Dict[str, str]] = None,
    generated_at: Optional[datetime] = None,
) -> Path:
    """Build a report from *result* and write it to *path*.

    The format is chosen by the file suffix (``.json`` / ``.csv``); anything
    else raises ``ValueError``. Returns the written path.
    """
    path = Path(path)
    writer = _SUFFIX_WRITERS.get(path.suffix.lower())
    if writer is None:
        raise ValueError(
            f"不支持的导出格式：{path.suffix or '(无扩展名)'}；"
            f"请使用 {', '.join(supported_formats())}。"
        )
    report = build_report(
        result,
        app_version=app_version,
        rules=rules,
        generated_at=generated_at,
    )
    return writer(report, path)
