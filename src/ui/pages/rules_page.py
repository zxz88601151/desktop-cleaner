"""Custom rules page (自定义规则) — V1.2-A, feature 4.

The user-facing surface for the resolution layer in
:mod:`core.custom_rules`:

    内置规则 + 我的规则  ->  生效规则

The page never re-implements any rule logic: it edits a
:class:`~core.custom_rules.RuleConfig`, hands it to
:func:`~core.custom_rules.save_config`, and displays whatever
:func:`~core.custom_rules.resolve_effective_rules` returns. Validation errors
come from :func:`~core.custom_rules.validate_config`, so the UI and the engine
can never disagree about what is valid.

Nothing here touches the filesystem.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.custom_rules import (
    ORIGIN_NEW,
    ORIGIN_OVERRIDE,
    RuleConfig,
    UserRule,
    builtin_by_category,
    effective_rules_fingerprint,
    load_config,
    normalize_extension,
    reset_config,
    resolve_effective_rules,
    save_config,
    user_rule_origin,
    validate_config,
    validate_extension,
)
from core.rules import CATEGORY_NAMES, DEFAULT_RULES, category_display
from ui.icons import color
from ui.theme_manager import ThemeManager
from ui.widgets.controls import ToggleSwitch

# Stable category key order for the combo boxes (display labels come from core).
_CATEGORY_ORDER = list(CATEGORY_NAMES.keys())

_ORIGIN_TEXT = {
    ORIGIN_OVERRIDE: "覆盖内置",
    ORIGIN_NEW: "新增",
}


def _category_combo(current: str) -> QComboBox:
    box = QComboBox()
    for key in _CATEGORY_ORDER:
        box.addItem(category_display(key), key)
    idx = box.findData(current)
    box.setCurrentIndex(idx if idx >= 0 else 0)
    return box


class RulesPage(QWidget):
    navigate = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._config: RuleConfig = RuleConfig()
        self._build()
        self._reload()
        ThemeManager.instance().on_changed(self._on_theme)

    # ----------------------------- build --------------------------------- #
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(18)

        title = QLabel("自定义规则")
        sub = QLabel("内置规则 + 你的规则 = 生效规则 — 只影响文件分类，不改变任何文件")
        sub.setObjectName("page-sub")
        root.addWidget(title)
        root.addWidget(sub)

        # ---- effective-rules summary ---- #
        card = QFrame()
        card.setObjectName("step-card")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(22, 22, 22, 22)
        cv.setSpacing(10)

        head = QLabel("生效规则概览")
        head.setObjectName("field-label")
        cv.addWidget(head)

        self._summary = QLabel()
        self._summary.setObjectName("summary-line")
        self._summary.setWordWrap(True)
        cv.addWidget(self._summary)

        self._fingerprint = QLabel()
        self._fingerprint.setObjectName("tl-sub")
        self._fingerprint.setWordWrap(True)
        cv.addWidget(self._fingerprint)

        self._issues = QLabel()
        self._issues.setObjectName("cat-ext")
        self._issues.setWordWrap(True)
        self._issues.setVisible(False)
        cv.addWidget(self._issues)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch(1)
        self._reset_btn = QPushButton("恢复默认")
        self._reset_btn.setObjectName("secondary")
        self._reset_btn.clicked.connect(self._reset)
        btn_row.addWidget(self._reset_btn)
        cv.addLayout(btn_row)
        root.addWidget(card)

        # ---- scrollable body ---- #
        self._stage = QScrollArea()
        self._stage.setWidgetResizable(True)
        self._stage.setFrameShape(QFrame.Shape.NoFrame)
        self._stage.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._stage_widget = QWidget()
        self._stage_lay = QVBoxLayout(self._stage_widget)
        self._stage_lay.setContentsMargins(0, 0, 0, 0)
        self._stage_lay.setSpacing(10)
        self._stage.setWidget(self._stage_widget)
        root.addWidget(self._stage, 1)

        self._build_user_section()
        self._build_builtin_section()
        self._stage_lay.addStretch(1)

    def _build_user_section(self):
        head = QLabel("我的规则")
        head.setObjectName("section-title")
        self._stage_lay.addWidget(head)

        panel = QFrame()
        panel.setObjectName("panel")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        add_row = QHBoxLayout()
        add_row.setSpacing(10)
        self._ext_input = QLineEdit()
        self._ext_input.setPlaceholderText("扩展名，例如 qqq（不含点）")
        self._ext_input.setMaxLength(20)
        self._ext_input.returnPressed.connect(self._add_rule)
        self._new_cat = _category_combo("images")
        add = QPushButton("添加规则")
        add.setObjectName("secondary")
        add.clicked.connect(self._add_rule)
        add_row.addWidget(self._ext_input, 1)
        add_row.addWidget(self._new_cat)
        add_row.addWidget(add)
        lay.addLayout(add_row)

        hint = QLabel("你的规则优先于内置规则；同一扩展名后添加的会覆盖先前的。")
        hint.setObjectName("cat-ext")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        self._user_list = QVBoxLayout()
        self._user_list.setSpacing(6)
        lay.addLayout(self._user_list)

        self._user_empty = QLabel("还没有自定义规则。")
        self._user_empty.setObjectName("tl-sub")
        lay.addWidget(self._user_empty)

        self._stage_lay.addWidget(panel)

    def _build_builtin_section(self):
        head = QLabel("内置规则")
        head.setObjectName("section-title")
        self._stage_lay.addWidget(head)

        panel = QFrame()
        panel.setObjectName("panel")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        self._search = QLineEdit()
        self._search.setPlaceholderText("搜索扩展名或类别，例如 pdf / 图片")
        self._search.textChanged.connect(lambda _t: self._render_builtins())
        lay.addWidget(self._search)

        self._builtin_count = QLabel()
        self._builtin_count.setObjectName("cat-ext")
        lay.addWidget(self._builtin_count)

        self._builtin_list = QVBoxLayout()
        self._builtin_list.setSpacing(4)
        lay.addLayout(self._builtin_list)

        self._stage_lay.addWidget(panel)

    # ----------------------------- data ----------------------------------- #
    def _reload(self):
        self._config = load_config()
        self._render_summary()
        self._render_user_rules()
        self._render_builtins()

    def _save(self):
        save_config(self._config)
        self._render_summary()

    # ----------------------------- render --------------------------------- #
    def _render_summary(self):
        effective = resolve_effective_rules(self._config)
        builtin_active = len(DEFAULT_RULES) - len(self._config.disabled_builtins)
        self._summary.setText(
            f"生效规则 {len(effective)} 条 · 内置 {len(DEFAULT_RULES)} 条"
            f"（已启用 {builtin_active} 条）· 我的规则 {len(self._config.user_rules)} 条"
        )
        self._fingerprint.setText(
            f"规则指纹：{effective_rules_fingerprint(effective)}"
            "（会写入导出的分析报告，便于比对）"
        )

        issues = validate_config(self._config)
        if issues:
            lines = [
                ("⚠ " if i.level == "warning" else "✕ ") + i.message for i in issues
            ]
            self._issues.setText("\n".join(lines))
            self._issues.setVisible(True)
        else:
            self._issues.setVisible(False)

        self._reset_btn.setDisabled(self._config.is_default)

    def _clear(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
            else:
                sub = item.layout()
                if sub is not None:
                    self._clear(sub)

    def _render_user_rules(self):
        self._clear(self._user_list)
        rules = self._config.user_rules
        self._user_empty.setVisible(not rules)

        for index, rule in enumerate(rules):
            row = QFrame()
            row.setObjectName("cat-row")
            rv = QHBoxLayout(row)
            rv.setContentsMargins(14, 10, 14, 10)
            rv.setSpacing(10)

            ext = QLabel(f".{rule.extension}")
            ext.setObjectName("cat-name")
            ext.setMinimumWidth(90)

            origin = QLabel(_ORIGIN_TEXT.get(user_rule_origin(rule.extension), ""))
            origin.setObjectName("tl-tag")

            combo = _category_combo(rule.category)
            combo.currentIndexChanged.connect(
                lambda _i, idx=index, box=combo: self._change_category(idx, box)
            )

            toggle = ToggleSwitch(rule.enabled)
            toggle.toggled.connect(lambda on, idx=index: self._toggle_rule(idx, on))

            delete = QPushButton("删除")
            delete.setObjectName("ghost")
            delete.clicked.connect(lambda _=False, idx=index: self._delete_rule(idx))

            rv.addWidget(ext)
            rv.addWidget(origin)
            rv.addStretch(1)
            rv.addWidget(combo)
            rv.addWidget(toggle)
            rv.addWidget(delete)
            self._user_list.addWidget(row)

    def _render_builtins(self):
        self._clear(self._builtin_list)
        needle = self._search.text().strip().lower()

        grouped = builtin_by_category()
        disabled = set(self._config.disabled_builtins)
        shown = 0
        for key in _CATEGORY_ORDER:
            exts = grouped.get(key, [])
            label = category_display(key)
            visible = [
                e for e in exts
                if not needle or needle in e or needle in label.lower()
            ]
            if not visible:
                continue
            for ext in visible:
                row = QFrame()
                row.setObjectName("cat-row")
                rv = QHBoxLayout(row)
                rv.setContentsMargins(14, 8, 14, 8)
                rv.setSpacing(10)

                cb = QCheckBox()
                cb.setChecked(ext not in disabled)
                cb.stateChanged.connect(
                    lambda _s, e=ext: self._toggle_builtin(e)
                )
                name = QLabel(f".{ext}")
                name.setObjectName("tl-title")
                name.setMinimumWidth(90)
                cat = QLabel(label)
                cat.setObjectName("tl-sub")

                rv.addWidget(cb)
                rv.addWidget(name)
                rv.addStretch(1)
                rv.addWidget(cat)
                self._builtin_list.addWidget(row)
                shown += 1

        self._builtin_count.setText(
            f"共 {len(DEFAULT_RULES)} 条内置规则，当前显示 {shown} 条"
            + (f"（已停用 {len(disabled)} 条）" if disabled else "")
        )

    # ----------------------------- actions -------------------------------- #
    def _add_rule(self):
        raw = self._ext_input.text()
        err = validate_extension(raw)
        if err:
            QMessageBox.warning(self, "无法添加", err)
            return
        ext = normalize_extension(raw)
        if any(r.extension == ext for r in self._config.user_rules):
            QMessageBox.information(
                self, "已存在", f"扩展名 .{ext} 已经在你的规则中，请直接修改它。"
            )
            return

        category = self._new_cat.currentData()
        self._config.user_rules.append(UserRule(ext, category, enabled=True))
        self._ext_input.clear()
        self._save()
        self._render_user_rules()

    def _change_category(self, index: int, box: QComboBox):
        if index >= len(self._config.user_rules):
            return
        rule = self._config.user_rules[index]
        category = box.currentData()
        if rule.category == category:
            return
        self._config.user_rules[index] = UserRule(
            rule.extension, category, rule.enabled
        )
        self._save()

    def _toggle_rule(self, index: int, on: bool):
        if index >= len(self._config.user_rules):
            return
        rule = self._config.user_rules[index]
        self._config.user_rules[index] = UserRule(rule.extension, rule.category, on)
        self._save()

    def _delete_rule(self, index: int):
        if index >= len(self._config.user_rules):
            return
        removed = self._config.user_rules.pop(index)
        self._save()
        self._render_user_rules()
        self._render_builtins()
        del removed

    def _toggle_builtin(self, ext: str):
        disabled = set(self._config.disabled_builtins)
        if ext in disabled:
            disabled.discard(ext)
        else:
            disabled.add(ext)
        self._config.disabled_builtins = sorted(disabled)
        self._save()
        self._render_builtins()

    def _reset(self):
        ans = QMessageBox.question(
            self,
            "恢复默认",
            "将删除你的全部自定义规则并重新启用所有内置规则。\n"
            "不会影响任何已整理的文件。是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        reset_config()
        self._reload()

    # ----------------------------- misc ----------------------------------- #
    def _on_theme(self):
        pass

    def on_enter(self):
        self._reload()
