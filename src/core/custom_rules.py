"""Custom rule resolution + validation (V1.2-A, feature 4).

The product ships a set of **built-in rules** (extension -> category). This
module lets a user customise that mapping without ever touching the built-in
table, and defines exactly how the two combine:

    effective rules = built-in rules (minus disabled) + user rules (last wins)

Design rules
------------
- **The built-in table is immutable at runtime.** Customisation is stored
  separately (a small JSON document in the settings KV store) and applied on
  top. ``core.rules.DEFAULT_RULES`` is never mutated, so "reset to default" is
  trivially correct and a corrupt user config can never brick classification.
- **Resolution is pure and total.** :func:`resolve_effective_rules` never
  raises: an invalid entry is dropped (and logged) rather than crashing the
  engine. Validation is a *separate*, explicit step
  (:func:`validate_config`) so the UI can show the user what is wrong while the
  engine keeps running on whatever is valid.
- **Categories are stable keys.** A rule's category must be a key of
  ``core.rules.CATEGORY_NAMES`` — never a display label.
- **Fail-safe on load.** Malformed stored JSON yields an empty config (i.e.
  pure defaults), never an exception.

Priority / conflict resolution (locked)
---------------------------------------
1. A user rule always beats a built-in rule for the same extension
   (an *override*).
2. Within the user rules, the **last** definition wins. The UI prevents
   duplicates, but the resolver stays deterministic even if one slips in.
3. A disabled built-in extension is simply absent from the effective map, so
   :func:`core.classifier.classify` falls back to ``others``. Disabling a
   built-in and overriding it to ``others`` are therefore equivalent, and both
   are supported.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .rules import CATEGORY_NAMES, DEFAULT_RULES, rules_fingerprint
from utils.logger import get_logger

_log = get_logger("custom_rules")

#: Settings KV key holding the serialised user configuration.
SETTINGS_KEY = "custom_rules"

#: Schema version of the stored document (bump on incompatible change).
CONFIG_VERSION = 1

#: Longest accepted extension (without the leading dot).
MAX_EXT_LEN = 16

# Extensions are matched against ``path.suffix``, i.e. a single token after the
# last dot — so compound extensions ("tar.gz") are intentionally not supported.
_EXT_RE = re.compile(r"^[a-z0-9][a-z0-9_+\-]*$")

#: Rule origins, as reported to the UI.
ORIGIN_BUILTIN = "builtin"
ORIGIN_OVERRIDE = "override"
ORIGIN_NEW = "new"


# --------------------------------------------------------------------------- #
# data model
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class UserRule:
    """One user-authored extension -> category mapping."""

    extension: str          # normalised: no dot, lower case
    category: str           # stable category key
    enabled: bool = True

    def to_dict(self) -> dict:
        return {
            "extension": self.extension,
            "category": self.category,
            "enabled": bool(self.enabled),
        }

    @classmethod
    def from_dict(cls, data) -> Optional["UserRule"]:
        """Tolerant parse: returns ``None`` for anything unusable."""
        if not isinstance(data, dict):
            return None
        ext = normalize_extension(data.get("extension"))
        cat = data.get("category")
        if not ext or cat not in CATEGORY_NAMES:
            return None
        return cls(extension=ext, category=cat, enabled=bool(data.get("enabled", True)))


@dataclass
class RuleConfig:
    """The user's stored customisation (never includes built-in rules)."""

    disabled_builtins: List[str] = field(default_factory=list)
    user_rules: List[UserRule] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "version": CONFIG_VERSION,
            "disabled_builtins": list(self.disabled_builtins),
            "user_rules": [r.to_dict() for r in self.user_rules],
        }

    @classmethod
    def from_dict(cls, data) -> "RuleConfig":
        """Tolerant parse — malformed input degrades to an empty config."""
        if not isinstance(data, dict):
            return cls()
        raw_disabled = data.get("disabled_builtins") or []
        disabled = sorted(
            {
                normalize_extension(x)
                for x in raw_disabled
                if isinstance(x, (str, int, float)) and normalize_extension(x)
            }
        )
        rules: List[UserRule] = []
        for item in data.get("user_rules") or []:
            rule = UserRule.from_dict(item)
            if rule is not None:
                rules.append(rule)
        return cls(disabled_builtins=disabled, user_rules=rules)

    @property
    def is_default(self) -> bool:
        return not self.disabled_builtins and not self.user_rules


@dataclass(frozen=True)
class Issue:
    """A validation finding. ``level`` is ``"error"`` or ``"warning"``."""

    level: str
    where: str
    message: str


# --------------------------------------------------------------------------- #
# normalisation + validation
# --------------------------------------------------------------------------- #
def normalize_extension(raw) -> str:
    """``".JPG"`` / ``" jpg "`` -> ``"jpg"``. Never raises."""
    if raw is None:
        return ""
    return str(raw).strip().lstrip(".").lower()


def validate_extension(raw) -> Optional[str]:
    """Return an error message, or ``None`` when the extension is usable."""
    ext = normalize_extension(raw)
    if not ext:
        return "扩展名不能为空。"
    if len(ext) > MAX_EXT_LEN:
        return f"扩展名过长（最多 {MAX_EXT_LEN} 个字符）。"
    if not _EXT_RE.match(ext):
        return "扩展名只能包含字母、数字、下划线、加号或连字符，且需以字母或数字开头。"
    return None


def validate_category(category) -> Optional[str]:
    """Return an error message, or ``None`` when the category is valid."""
    if category not in CATEGORY_NAMES:
        return f"未知类别：{category!r}。"
    return None


def validate_config(config: RuleConfig) -> List[Issue]:
    """Check a config, returning every problem found (empty list == valid).

    Duplicate extensions across user rules are reported as **errors**; a user
    rule that shadows a built-in is fine (that is an intentional override).
    """
    issues: List[Issue] = []

    seen: Dict[str, int] = {}
    for i, rule in enumerate(config.user_rules):
        where = f"user_rules[{i}]"
        err = validate_extension(rule.extension)
        if err:
            issues.append(Issue("error", where, err))
        err = validate_category(rule.category)
        if err:
            issues.append(Issue("error", where, err))
        if rule.extension in seen:
            issues.append(
                Issue(
                    "error",
                    where,
                    f"扩展名 {rule.extension!r} 重复定义"
                    f"（首次出现在 user_rules[{seen[rule.extension]}]）。",
                )
            )
        else:
            seen[rule.extension] = i

    for i, ext in enumerate(config.disabled_builtins):
        err = validate_extension(ext)
        if err:
            issues.append(Issue("error", f"disabled_builtins[{i}]", err))
        elif ext not in DEFAULT_RULES:
            issues.append(
                Issue("warning", f"disabled_builtins[{i}]", f"{ext!r} 不是内置扩展名。")
            )

    return issues


# --------------------------------------------------------------------------- #
# resolution
# --------------------------------------------------------------------------- #
def resolve_effective_rules(
    config: Optional[RuleConfig] = None,
    builtin: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """Combine built-in and user rules into the effective map (pure, total).

    Never raises: invalid user rules are skipped and logged. See the module
    docstring for the locked priority rules.
    """
    config = config or RuleConfig()
    builtin = DEFAULT_RULES if builtin is None else builtin

    disabled = set(config.disabled_builtins)
    effective: Dict[str, str] = {
        ext: cat for ext, cat in builtin.items() if ext not in disabled
    }

    for rule in config.user_rules:
        if not rule.enabled:
            continue
        if validate_extension(rule.extension) or validate_category(rule.category):
            _log.warning("CUSTOM RULE skipped invalid ext=%r cat=%r",
                         rule.extension, rule.category)
            continue
        effective[rule.extension] = rule.category   # last wins

    return effective


def effective_rules_fingerprint(rules: Optional[Dict[str, str]] = None) -> str:
    """Fingerprint of the effective rule set (delegates to core.rules)."""
    return rules_fingerprint(DEFAULT_RULES if rules is None else rules)


def user_rule_origin(extension, builtin: Optional[Dict[str, str]] = None) -> str:
    """Describe a **user-authored** rule: does it override or add?

    ``override`` — the extension already exists in the built-in table, so the
    user rule replaces that mapping. ``new`` — the extension is user-only.
    """
    builtin = DEFAULT_RULES if builtin is None else builtin
    return (
        ORIGIN_OVERRIDE
        if normalize_extension(extension) in builtin
        else ORIGIN_NEW
    )


def builtin_by_category(builtin: Optional[Dict[str, str]] = None) -> Dict[str, List[str]]:
    """Group built-in extensions by category key (for the UI list)."""
    builtin = DEFAULT_RULES if builtin is None else builtin
    grouped: Dict[str, List[str]] = {key: [] for key in CATEGORY_NAMES}
    for ext, cat in builtin.items():
        grouped.setdefault(cat, []).append(ext)
    for exts in grouped.values():
        exts.sort()
    return grouped


# --------------------------------------------------------------------------- #
# persistence (settings KV store; no Qt, no direct SQL)
# --------------------------------------------------------------------------- #
def load_config() -> RuleConfig:
    """Read the user config. Corrupt / missing data -> an empty config."""
    from data import settings_repo

    raw = settings_repo.get(SETTINGS_KEY)
    if not raw:
        return RuleConfig()
    try:
        return RuleConfig.from_dict(json.loads(raw))
    except (ValueError, TypeError) as exc:
        _log.warning("CUSTOM RULES unreadable config, falling back to defaults: %s", exc)
        return RuleConfig()


def save_config(config: RuleConfig) -> None:
    """Persist the user config as JSON."""
    from data import settings_repo

    settings_repo.set(
        SETTINGS_KEY, json.dumps(config.to_dict(), ensure_ascii=False, sort_keys=True)
    )


def reset_config() -> None:
    """Drop all customisation -> the effective rules become the built-ins."""
    from data import settings_repo

    settings_repo.set(SETTINGS_KEY, "")


def effective_rules() -> Dict[str, str]:
    """The rule map the engine should use right now (load + resolve)."""
    return resolve_effective_rules(load_config())
