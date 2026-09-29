"""V1.2-A feature 4 — custom rule resolution + validation (Qt-free).

Run:  pytest tests/test_custom_rules.py   (or: python tests/test_custom_rules.py)

Properties asserted here:
  - extension / category validation rejects the documented bad inputs
  - resolution = built-in (minus disabled) + user rules, with the locked
    priority: user beats built-in; last user definition wins
  - resolution is TOTAL: invalid entries are dropped, never raised
  - duplicates are reported by validate_config (the UI's job) while the
    resolver still stays deterministic
  - the built-in table is never mutated by customisation
  - persistence round-trips through the settings KV store, and corrupt stored
    data degrades to defaults instead of crashing
  - the engine actually honours the effective rules (classify end-to-end)
  - the rules fingerprint tracks customisation
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

_TMP_HOME = tempfile.mkdtemp(prefix="dc_rules_")
os.environ["DESKTOP_CLEANER_HOME"] = _TMP_HOME

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core import classify  # noqa: E402
from core.custom_rules import (  # noqa: E402
    SETTINGS_KEY,
    Issue,
    RuleConfig,
    UserRule,
    builtin_by_category,
    effective_rules,
    effective_rules_fingerprint,
    load_config,
    normalize_extension,
    reset_config,
    resolve_effective_rules,
    save_config,
    user_rule_origin,
    validate_category,
    validate_config,
    validate_extension,
)
from core.rules import CATEGORY_NAMES, DEFAULT_RULES, rules_fingerprint  # noqa: E402
from data import database, settings_repo  # noqa: E402

database.init_db()

_BUILTIN_SNAPSHOT = dict(DEFAULT_RULES)


def _assert(cond: bool, msg: str):
    if not cond:
        raise AssertionError("FAIL: " + msg)
    print("  ok:", msg)


# --------------------------------------------------------------------------- #
def test_normalise():
    print("[1] normalise_extension")
    _assert(normalize_extension(".JPG") == "jpg", "leading dot + case stripped")
    _assert(normalize_extension("  PDF ") == "pdf", "whitespace stripped")
    _assert(normalize_extension(None) == "", "None -> empty")
    _assert(normalize_extension("") == "", "empty stays empty")


def test_validate_extension():
    print("[2] validate_extension")
    _assert(validate_extension("jpg") is None, "plain extension ok")
    _assert(validate_extension(".JPG") is None, "normalised form ok")
    _assert(validate_extension("7z") is None, "digit-leading ok")
    _assert(validate_extension("x" * 17) is not None, "too long rejected")
    _assert(validate_extension("a" * 16) is None, "16 chars accepted")
    _assert(validate_extension("") is not None, "empty rejected")
    _assert(validate_extension("a b") is not None, "space rejected")
    _assert(validate_extension("a/b") is not None, "slash rejected")
    _assert(validate_extension("a.b") is not None, "inner dot rejected")
    _assert(validate_extension("-x") is not None, "must start alphanumeric")


def test_validate_category():
    print("[3] validate_category uses stable keys only")
    _assert(validate_category("images") is None, "known key accepted")
    _assert(validate_category("图片") is not None, "a UI label is NOT a category")
    _assert(validate_category("nope") is not None, "unknown key rejected")
    _assert(validate_category(None) is not None, "None rejected")


def test_default_resolution_is_the_builtin_table():
    print("[4] no customisation -> effective rules == built-ins")
    eff = resolve_effective_rules(RuleConfig())
    _assert(eff == DEFAULT_RULES, "empty config resolves to the built-in table")
    _assert(eff is not DEFAULT_RULES, "and it is a copy, not the table itself")


def test_disabled_builtin_is_removed():
    print("[5] disabled built-in disappears -> classify falls back to others")
    cfg = RuleConfig(disabled_builtins=["pdf"])
    eff = resolve_effective_rules(cfg)
    _assert("pdf" not in eff, "pdf removed")
    _assert(eff["docx"] == "documents", "other built-ins untouched")
    _assert(classify(Path("a.pdf"), eff) == "others", "classify -> others")
    _assert(classify(Path("a.pdf"), DEFAULT_RULES) == "documents",
            "the built-in table itself is unchanged")


def test_user_rule_adds_and_overrides():
    print("[6] user rules add new mappings and override built-ins")
    cfg = RuleConfig(user_rules=[
        UserRule("qqq", "images"),
        UserRule("pdf", "images"),
    ])
    eff = resolve_effective_rules(cfg)
    _assert(eff["qqq"] == "images", "new extension added")
    _assert(eff["pdf"] == "images", "built-in overridden by the user rule")
    _assert(classify(Path("x.qqq"), eff) == "images", "engine honours the new rule")
    _assert(classify(Path("x.pdf"), eff) == "images", "engine honours the override")
    _assert(DEFAULT_RULES["pdf"] == "documents", "built-ins never mutated")


def test_disabled_user_rule_is_ignored():
    print("[7] a disabled user rule has no effect")
    cfg = RuleConfig(user_rules=[UserRule("qqq", "images", enabled=False)])
    eff = resolve_effective_rules(cfg)
    _assert("qqq" not in eff, "disabled rule not applied")
    _assert(eff == DEFAULT_RULES, "effective rules stay default")


def test_duplicates_are_deterministic_and_flagged():
    print("[8] duplicate extensions: flagged by validation, deterministic in resolve")
    cfg = RuleConfig(user_rules=[
        UserRule("qqq", "images"),
        UserRule("qqq", "videos"),
    ])
    issues = validate_config(cfg)
    errs = [i for i in issues if i.level == "error"]
    _assert(any("重复" in i.message for i in errs), "duplicate reported as an error")
    eff = resolve_effective_rules(cfg)
    _assert(eff["qqq"] == "videos", "last definition wins (deterministic)")


def test_resolution_is_total():
    print("[9] resolution never raises on invalid entries")
    cfg = RuleConfig(
        disabled_builtins=["pdf", ""],
        user_rules=[
            UserRule("ok1", "images"),
            UserRule("bad ext", "images"),     # invalid extension
            UserRule("ok2", "not_a_category"),  # invalid category
        ],
    )
    eff = resolve_effective_rules(cfg)
    _assert(eff["ok1"] == "images", "valid rule applied")
    _assert("ok2" not in eff, "invalid category dropped")
    _assert("bad ext" not in eff, "invalid extension dropped")
    _assert("pdf" not in eff, "disabled built-in still removed")


def test_validate_config_warnings():
    print("[10] validate_config separates errors from warnings")
    cfg = RuleConfig(disabled_builtins=["zzz"])   # valid shape, not a built-in
    issues = validate_config(cfg)
    _assert(len(issues) == 1 and issues[0].level == "warning",
            f"unknown built-in is a warning (got {issues})")
    _assert(validate_config(RuleConfig()) == [], "a clean config has no issues")

    # an over-long extension is an ERROR, not a warning
    long_cfg = RuleConfig(disabled_builtins=["not_a_builtin_ext_zzz"])
    _assert(all(i.level == "error" for i in validate_config(long_cfg)),
            "an invalid extension is an error even in the disabled list")

    bad = RuleConfig(user_rules=[UserRule("jpg", "nope")])
    _assert(any(i.level == "error" for i in validate_config(bad)),
            "bad category is an error")
    _assert(all(isinstance(i, Issue) for i in validate_config(bad)), "returns Issues")


def test_config_round_trip_and_tolerance():
    print("[11] RuleConfig serialises and tolerates garbage")
    cfg = RuleConfig(
        disabled_builtins=["pdf", ".ZIP"],
        user_rules=[UserRule(".QQQ", "images", enabled=False)],
    )
    back = RuleConfig.from_dict(json.loads(json.dumps(cfg.to_dict())))
    _assert(back.disabled_builtins == ["pdf", "zip"],
            f"disabled list normalised + sorted (got {back.disabled_builtins})")
    _assert(back.user_rules == [UserRule("qqq", "images", enabled=False)],
            "user rule round-trips normalised")

    _assert(RuleConfig.from_dict(None).is_default, "None -> default config")
    _assert(RuleConfig.from_dict("junk").is_default, "a string -> default config")
    _assert(RuleConfig.from_dict({"user_rules": "junk"}).is_default,
            "a bad user_rules value -> default config")
    _assert(RuleConfig.from_dict({"user_rules": [{"extension": "x"}]}).user_rules == [],
            "an entry missing its category is dropped")
    _assert(RuleConfig().is_default, "a fresh config is the default")


def test_persistence_through_settings():
    print("[12] persistence: save / load / reset via the settings store")
    reset_config()
    _assert(load_config().is_default, "reset -> default")
    _assert(effective_rules() == DEFAULT_RULES, "effective rules back to built-ins")

    save_config(RuleConfig(user_rules=[UserRule("qqq", "images")]))
    _assert(load_config().user_rules == [UserRule("qqq", "images")], "saved + loaded")
    eff = effective_rules()
    _assert(eff["qqq"] == "images", "effective_rules() applies the saved config")
    _assert(eff["pdf"] == "documents", "built-ins still present")

    # corrupt the stored document -> must degrade, not crash
    settings_repo.set(SETTINGS_KEY, "{not json")
    _assert(load_config().is_default, "corrupt stored JSON -> default config")
    _assert(effective_rules() == DEFAULT_RULES, "and effective rules are the built-ins")

    reset_config()
    _assert(effective_rules() == DEFAULT_RULES, "reset works from a corrupt state")


def test_fingerprint_tracks_customisation():
    print("[13] the rules fingerprint tracks customisation")
    base_fp = effective_rules_fingerprint(DEFAULT_RULES)
    _assert(base_fp == rules_fingerprint(DEFAULT_RULES), "default fingerprint")
    cfg = RuleConfig(user_rules=[UserRule("qqq", "images")])
    custom = resolve_effective_rules(cfg)
    _assert(effective_rules_fingerprint(custom) != base_fp,
            "customisation changes the fingerprint")


def test_helpers():
    print("[14] origin + grouping helpers")
    _assert(user_rule_origin("pdf") == "override", "pdf overrides a built-in")
    _assert(user_rule_origin("qqq") == "new", "qqq is new")
    _assert(user_rule_origin(".PDF") == "override", "normalised before lookup")

    grouped = builtin_by_category()
    _assert(set(grouped) == set(CATEGORY_NAMES), "one group per category key")
    _assert("jpg" in grouped["images"], "jpg grouped under images")
    _assert(sum(len(v) for v in grouped.values()) == len(DEFAULT_RULES),
            "every built-in appears exactly once")


def test_builtin_table_never_mutated():
    print("[15] the built-in table is never mutated by customisation")
    save_config(RuleConfig(
        disabled_builtins=["pdf"],
        user_rules=[UserRule("pdf", "images"), UserRule("qqq", "videos")],
    ))
    effective_rules()
    _assert(DEFAULT_RULES == _BUILTIN_SNAPSHOT,
            "DEFAULT_RULES is byte-for-byte identical to the module-load snapshot")
    reset_config()
    _assert(DEFAULT_RULES == _BUILTIN_SNAPSHOT, "and still identical after reset")


def main():
    database.init_db()
    test_normalise()
    test_validate_extension()
    test_validate_category()
    test_default_resolution_is_the_builtin_table()
    test_disabled_builtin_is_removed()
    test_user_rule_adds_and_overrides()
    test_disabled_user_rule_is_ignored()
    test_duplicates_are_deterministic_and_flagged()
    test_resolution_is_total()
    test_validate_config_warnings()
    test_config_round_trip_and_tolerance()
    test_persistence_through_settings()
    test_fingerprint_tracks_customisation()
    test_helpers()
    test_builtin_table_never_mutated()
    print("\nALL CUSTOM-RULE TESTS PASSED")


if __name__ == "__main__":
    try:
        main()
    finally:
        shutil.rmtree(_TMP_HOME, ignore_errors=True)
