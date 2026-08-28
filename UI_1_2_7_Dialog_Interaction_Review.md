# UI-1.2.7 — Dialog Interaction Review

## 1. 阶段
UI-1.2.7

## 2. 执行模式
READ → AUDIT → MINIMAL FIX → TEST → STOP

## 3. 修改文件
- `src/ui/preview_report.py` — 新增「整理方式」标签（按类型 / 按日期），读取 `report.get("mode")`。
- `src/ui/pages/organize_page.py` — 在弹出 Preview 前追加 `report["mode"] = self._mode`（仅 UI 编排层，未改 core）。
- `src/ui/about.py` — About 关闭按钮补充 `setDefault(True)`，保证 Enter 可靠关闭。
- `src/ui/undo.py` — `ConfirmUndoDialog` 补充 `setModal(True)`；复用已有 `history_repo.get(hid)` 读取整理时间并显示「整理时间：YYYY-MM-DD HH:MM」；正文追加诚实提示「若原位置已被改动或发生冲突，部分文件可能无法恢复。」（复用 `run_undo` 既有的 `failed_files` 部分失败机制，仅展示文案，未改业务逻辑 / 数据库结构）。

未修改：`core/*`、`data/*` 结构、`organizer`、`scanner`、`worker`、`ui/undo.py` 的业务编排逻辑、数据库。

## 4. Dialog Matrix

| Dialog | Modal | Enter | Escape | X | CTA |
|---|---|---|---|---|---|
| Welcome | PASS | PASS | PASS | PASS | PASS |
| About | PASS | PASS | PASS | PASS | PASS |
| Preview | PASS | PASS | PASS | PASS | PASS |
| Undo | PASS | PASS | PASS | PASS | PASS |

说明：
- **Welcome**：`setModal(True)`；CTA「开始使用」`setDefault(True)` → Enter 触发 accept；X / Esc → `reject`，**不会**写入 `first_launch_completed`（该标志仅在重写的 `accept()` 内写入）。安全。
- **About**：`setModal(True)`；单按钮「关闭」`setDefault(True)` → Enter 关闭；X / Esc → `reject` 关闭。信息类，无强操作。
- **Preview**：`setModal(True)`；「开始整理」`setDefault(True)` → Enter 开始；「取消」`ghost` → `reject`；X / Esc → `reject`，**不会**误触整理。
- **Undo**：`exec()` 应用模态 + 本次补 `setModal(True)`；「还原」`undo-cta` 为 `QDialogButtonBox` 默认按钮 → Enter 还原；「取消」`ghost` → `reject`；X / Esc → `reject`，**不会**误触还原。

## 5. Safety

Preview:
- 不会误触整理。Enter 仅由显式 `setDefault` 的「开始整理」触发；X / Esc / 双击均走 `reject`，且代码无任何 `keyPressEvent` 重写将 X 映射为确认。

Undo:
- 不会误触还原。同上，`reject` 路径关闭，不调用 `run_undo`。

X:
- Preview / Undo / Welcome / About 全部 X = `reject` / 关闭，均 ≠ Confirm / Start / Undo。

Escape:
- 全部走 `reject`，≠ 强操作。

## 6. Visual Hierarchy

标题：PASS —— Welcome「欢迎使用 Desktop Cleaner」、About「关于」、Preview「整理模拟报告」、Undo「撤销本次整理？」均存在且使用 `#dialog-title` / `#welcome-title` 等专用 QSS。

说明：PASS —— 每个 Dialog 在标题下均有说明行（Welcome 副标题 + 6 条 ✓ 承诺；About 标语 + 能力列表；Preview 目标文件夹 + 整理方式 + 摘要；Undo 还原说明）。

内容：PASS —— Preview 含「目标文件夹 / 整理方式 / 文件数 + 大小 / 分类表格 / 移动明细 / 行为说明」；Undo 含「文件数 / 原路径 / 整理时间 / 行为说明 / 诚实提示」；结构为 标题 → 说明 → 内容 → 按钮，无大段空白。

按钮：PASS —— 双按钮 Dialog 统一「Ghost 左 / Primary·Undo 右」（Preview cancel→ok；Undo Cancel|Ok 默认左取消右确认）；About / Welcome 单 Primary 右对齐。CTA 文案统一：Preview「开始整理」、Undo「还原」、Welcome「开始使用」、About「关闭」，未使用「确认 / 确定 / 执行 / 继续 / OK」。

## 7. Accessibility
Focus: PASS —— 所有按钮沿用 UI-1.2.2 全局 `:focus` 焦点环；`setDefault` 明确默认聚焦按钮。

Keyboard: PASS —— Enter（默认按钮）/ Esc（reject）/ Tab（默认 Tab 序）均可操作；未新增任何 `Ctrl+` / `Alt+` / `F1` 快捷键。

Tooltip: PASS —— 主题切换图标按钮已在 UI-1.2.6 设置 `setToolTip("切换主题（浅色 / 深色）")`；其余按钮均有明确中文文字，无「纯 Icon 无文字」操作按钮。

## 8. Problems
NONE

（审计发现的 3 处显式缺口已在本阶段以最小修改补齐：Preview 缺「整理方式」、Undo 缺「整理时间」与部分失败诚实提示、About 缺 `setDefault`。）

## 9. P2 Notes
- (a) `#report-mode` 标签当前无专属 QSS（继承默认文本），可读性无碍；如需强化层级可在 UI-1.3 Typography 阶段补样式。
- (b) Preview `setMinimumSize(680,580)`、Undo `setMinimumWidth(420)` 为最小尺寸而非固定尺寸，配合内容自适应，100% / 125% / 150% DPI 下不会挤压或溢出；未做死尺寸，PASS。
- (c) Undo「整理时间」仅在对应 history 记录存在时显示（headless 测试用不存在的 hid 时优雅隐藏），符合「若数据结构能提供则使用现有数据」原则。
- (d) About 单按钮「关闭」= Primary（UI-1.2.6 已确认接受）。
- (e) `QMessageBox.information/warning/critical` 均为动作后的结果通知，默认模态、Enter 关闭，非安全门，无风险。

## 10. Tests
compileall: PASS
test_core: PASS
test_security: PASS
test_reliability: PASS
test_windows_paths: PASS
test_p2_coverage: PASS

附加 headless 渲染校验（offscreen）：4 个 Dialog 均成功构造；Preview 含「按类型整理」且 modal；Undo modal 且含诚实提示；Welcome / About modal。

## 11. Final Verdict
PASS

## 12. Next Stage
UI-1.2.8 — Button System Final Freeze

等待确认，不得自动进入下一阶段。

建议：若 UI-1.2.7 PASS，下一步直接「冻结」Button System —— 做最后一次全量静态检查后打上 **FROZEN**，不再无休止抠按钮。随后进入 UI-1.3 Design System（Card / Typography / Spacing / Empty / Loading / Error / Toast / Progress / List / Badge / Status 统一），再进入 UI-2 Tools Hub + Feature Registry + Coming Soon，正式搭建「中哥工具箱」。
