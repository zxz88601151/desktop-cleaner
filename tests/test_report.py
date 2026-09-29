"""V1.2-A feature 3 — report export (Qt-free).

Run:  pytest tests/test_report.py       (or: python tests/test_report.py)

Properties asserted here:
  - the report carries schema / time / app version / rules fingerprint
  - JSON is plain UTF-8, stable-fielded and round-trips
  - CSV is one strict RFC-4180 table (utf-8-sig) with the documented sections
  - CSV numbers stay numeric and Chinese paths survive the round-trip
  - category identity in the DATA is the stable key, never a UI label
  - rules_fingerprint is a pure function of rule contents
  - export() dispatches on the suffix and rejects anything else
"""
import csv
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

_TMP_HOME = tempfile.mkdtemp(prefix="dc_report_")
os.environ["DESKTOP_CLEANER_HOME"] = _TMP_HOME

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core import analyze, export  # noqa: E402
from core.report import (  # noqa: E402
    CSV_COLUMNS,
    REPORT_SCHEMA,
    build_report,
    supported_formats,
    write_csv,
    write_json,
)
from core.rules import DEFAULT_RULES, rules_fingerprint  # noqa: E402
from data import database  # noqa: E402

database.init_db()

_FIXED = datetime(2026, 9, 29, 10, 11, 12, tzinfo=timezone.utc)


def _assert(cond: bool, msg: str):
    if not cond:
        raise AssertionError("FAIL: " + msg)
    print("  ok:", msg)


def _tree() -> Path:
    """A tree that also exercises non-ASCII paths."""
    base = Path(tempfile.mkdtemp(prefix="dc_r_"))
    (base / "文档").mkdir()
    (base / "图片").mkdir()
    (base / "空目录").mkdir()
    (base / "文档" / "a.pdf").write_bytes(b"a" * 100)
    (base / "文档" / "b.txt").write_bytes(b"b" * 200)
    (base / "图片" / "c.jpg").write_bytes(b"c" * 1000)
    (base / "notes.md").write_bytes(b"n" * 50)
    return base


def _report(base: Path) -> dict:
    return build_report(
        analyze(base),
        app_version="1.1.1",
        generated_at=_FIXED,
    )


# --------------------------------------------------------------------------- #
def test_report_provenance_and_shape():
    print("[1] report provenance + shape")
    r = _report(_tree())
    _assert(r["schema"] == REPORT_SCHEMA, "schema recorded")
    _assert(r["generated_at"] == "2026-09-29T10:11:12+00:00",
            f"generated_at is ISO-8601 with offset (got {r['generated_at']})")
    _assert(r["generated_at_epoch"] == int(_FIXED.timestamp()),
            "generated_at_epoch is the same instant")
    _assert(r["app_version"] == "1.1.1", "app version recorded")
    _assert(r["rules_version"].startswith("rules-"), "rules fingerprint recorded")
    _assert(r["rules_count"] == len(DEFAULT_RULES), "rules count recorded")
    _assert(r["analysis"]["total_size_bytes"] == 1350, "analysis payload attached")
    _assert("size_unit" in r["notes"] and r["notes"]["size_unit"] == "bytes",
            "units are declared explicitly")
    _assert("empty_folder_semantics" in r["notes"],
            "empty-folder semantics are declared explicitly")


def test_data_uses_stable_keys_never_ui_text():
    print("[2] data carries stable keys; labels are a separate display aid")
    r = _report(_tree())
    cats = {e["category"] for e in r["analysis"]["by_category"]}
    _assert(cats == {"documents", "images"}, f"stable keys only (got {cats})")
    _assert(
        r["category_labels"]["documents"] == "文档",
        "labels live in their own block, clearly separate from the data",
    )
    _assert(
        "category" in r["analysis"]["by_category"][0]
        and "label" not in r["analysis"]["by_category"][0],
        "no label field on a data record",
    )


def test_json_is_utf8_and_round_trips():
    print("[3] JSON is plain UTF-8 and round-trips")
    base = _tree()
    out = Path(tempfile.mkdtemp(prefix="dc_r3_")) / "report.json"
    write_json(_report(base), out)
    raw = out.read_bytes()
    _assert(not raw.startswith(b"\xef\xbb\xbf"), "JSON has no BOM (plain UTF-8)")
    back = json.loads(raw.decode("utf-8"))
    _assert(back["schema"] == REPORT_SCHEMA, "schema survives the round-trip")
    _assert(back["analysis"]["file_count"] == 4, "file_count survives")
    _assert(
        any("文档" in f["path"] for f in back["analysis"]["largest_files"]),
        "non-ASCII paths survive as real UTF-8",
    )


def test_csv_is_one_strict_table_with_sections():
    print("[4] CSV is one strict RFC-4180 table with the documented sections")
    base = _tree()
    out = Path(tempfile.mkdtemp(prefix="dc_r4_")) / "report.csv"
    write_csv(_report(base), out)

    with open(out, "r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    _assert(tuple(rows[0]) == tuple(CSV_COLUMNS),
            f"single header row (got {rows[0]})")
    _assert(all(len(r) == len(CSV_COLUMNS) for r in rows),
            "every row has the same column count (strict table)")

    sections = {r[0] for r in rows[1:]}
    for expected in ("summary", "category", "extension",
                     "largest_file", "largest_folder",
                     "recent_file", "empty_folder"):
        _assert(expected in sections, f"section present: {expected}")

    summary = {r[1]: r[7] for r in rows[1:] if r[0] == "summary"}
    _assert(summary["total_size_bytes"] == "1350", "summary total_size_bytes")
    _assert(summary["file_count"] == "4", "summary file_count")
    _assert(summary["rules_version"].startswith("rules-"), "summary rules_version")
    _assert(summary["schema"] == REPORT_SCHEMA, "summary schema")

    cats = {r[1]: (r[2], r[3]) for r in rows[1:] if r[0] == "category"}
    _assert(cats["images"] == ("1", "1000"), f"category images row (got {cats.get('images')})")
    _assert(cats["documents"] == ("3", "350"), "category documents row")

    largest = [r for r in rows[1:] if r[0] == "largest_file"]
    _assert(len(largest) == 4, "one row per analysed file")
    _assert(largest[0][3] == "1000", "largest file first, real byte size")
    _assert(largest[0][5].endswith("c.jpg"), "largest file path recorded")

    empties = [r for r in rows[1:] if r[0] == "empty_folder"]
    _assert(len(empties) == 1 and empties[0][5].endswith("空目录"),
            "empty folder exported with its real path")


def test_csv_has_bom_for_excel_and_keeps_chinese():
    print("[5] CSV is UTF-8 with BOM so Excel renders Chinese correctly")
    base = _tree()
    out = Path(tempfile.mkdtemp(prefix="dc_r5_")) / "report.csv"
    write_csv(_report(base), out)
    raw = out.read_bytes()
    _assert(raw.startswith(b"\xef\xbb\xbf"), "BOM present")
    text = raw.decode("utf-8-sig")  # must decode as UTF-8 once the BOM is stripped
    _assert("文档" in text and "空目录" in text, "Chinese paths intact")


def test_rules_fingerprint_is_a_pure_function():
    print("[6] rules_fingerprint is a pure function of rule contents")
    a = rules_fingerprint(DEFAULT_RULES)
    b = rules_fingerprint(dict(DEFAULT_RULES))
    _assert(a == b, "same contents -> same fingerprint")
    _assert(a.startswith("rules-") and a.endswith(f"-{len(DEFAULT_RULES)}"),
            f"fingerprint shape (got {a})")

    changed = dict(DEFAULT_RULES)
    changed["qqq"] = "images"
    _assert(rules_fingerprint(changed) != a, "adding a rule changes the fingerprint")

    moved = dict(DEFAULT_RULES)
    moved["pdf"] = "images"
    _assert(rules_fingerprint(moved) != a, "re-mapping an extension changes it")

    # a report records the fingerprint of the rules it was produced with
    r = build_report(analyze(_tree()), rules=changed, generated_at=_FIXED)
    _assert(r["rules_version"] == rules_fingerprint(changed),
            "report records the supplied rule set, not the default")


def test_export_dispatch():
    print("[7] export() dispatches on the suffix")
    base = _tree()
    result = analyze(base)
    d = Path(tempfile.mkdtemp(prefix="dc_r7_"))

    j = export(result, d / "r.json", app_version="9.9.9", generated_at=_FIXED)
    c = export(result, d / "r.csv", app_version="9.9.9", generated_at=_FIXED)
    _assert(j.exists() and j.suffix == ".json", "json written")
    _assert(c.exists() and c.suffix == ".csv", "csv written")
    _assert(json.loads(j.read_text(encoding="utf-8"))["app_version"] == "9.9.9",
            "app version flows through export()")
    _assert(".csv" in supported_formats() and ".json" in supported_formats(),
            f"supported formats advertised (got {supported_formats()})")

    up = export(result, d / "R.CSV", app_version="9.9.9", generated_at=_FIXED)
    _assert(up.exists(), "suffix matching is case-insensitive")

    raised = False
    try:
        export(result, d / "r.txt")
    except ValueError:
        raised = True
    _assert(raised, "an unsupported suffix raises ValueError")


def main():
    database.init_db()
    test_report_provenance_and_shape()
    test_data_uses_stable_keys_never_ui_text()
    test_json_is_utf8_and_round_trips()
    test_csv_is_one_strict_table_with_sections()
    test_csv_has_bom_for_excel_and_keeps_chinese()
    test_rules_fingerprint_is_a_pure_function()
    test_export_dispatch()
    print("\nALL REPORT TESTS PASSED")


if __name__ == "__main__":
    try:
        main()
    finally:
        shutil.rmtree(_TMP_HOME, ignore_errors=True)
