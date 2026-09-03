# UI-1.2.6 — Focus / Pressed / Keyboard Interaction Final Review

## 1. 阶段
UI-1.2.6

## 2. 执行模式
READ ONLY 审计 → 发现 1 项可修 Enter 默认按钮缺陷 + 1 项 Icon 可访问提示缺失 → AUDIT + MINIMAL FIX

## 3. 修改文件
| 文件 | 改动 | 性质 |
|------|------|------|
| `src/ui/preview_report.py` | `ok_btn.setDefault(True)`（开始整理=默认按钮） | UI 调用处最小修复 |
| `src/ui/welcome.py` | `start_btn.setDefault(True)`（开始使用=默认按钮） | UI 调用处最小修复 |
| `src/ui/app_shell.py` | `self.theme_btn.setToolTip("切换主题（浅色 / 深色）")` | Icon 可访问提示 |

> `src/ui/undo.py` 的确认弹窗**无需修改**：`QDialogButtonBox(Ok\|Cancel)` 自动将 Ok(还原) 设为 default，`Enter→还原 / Esc→取消` 已成立。
> 未触碰 `core/*`、`data/*`、`ui/undo.py` 业务逻辑、`ui/state/worker.py`、`utils/*`。

## 4. Focus
Primary: PASS
Secondary: PASS
Tertiary: PASS
Ghost: PASS
Undo: PASS
Danger: PASS（0 实例，预留）
Icon: PASS

全局 `QPushButton:focus { outline: 2px solid {accent}; outline-offset: 2px; }` 覆盖全部变体，token 驱动、不改变布局、不破坏圆角、与 hover 可正常叠加（克制）。Light/Dark 双主题渲染校验通过。

## 5. Pressed
Primary: PASS
Secondary: PASS
Tertiary: PASS
Ghost: PASS
Undo: PASS
Icon: PASS

逐个变体核对 `normal / hover / pressed / focus` 四态齐全；`disabled` 由基础 `QPushButton:disabled` 统一覆盖。
**布局抖动检查（§6 P1 红线）**：所有变体（含 tertiary/ghost）border 宽度在 normal/hover/pressed 恒为 1px，仅 background/color 变化 → **无占位尺寸变化，无布局抖动**。PASS。

## 6. Keyboard

### Enter
Preview → 开始整理：PASS（补 `setDefault(True)`）
Welcome → 开始使用：PASS（补 `setDefault(True)`）
Undo → 还原：PASS（QDialogButtonBox 自动 default）
Other dialogs：无 Enter 强操作风险

### Escape
Dialog → Cancel/Close：PASS
Welcome / About / Preview / Undo 四个 Dialog 均无 `keyPressEvent` 覆盖，Qt 默认 `Esc→reject`（安全退出）。Escape 绝不会触发 整理/还原/删除。

### Tab
主要页面：PASS（控件按创建顺序自上而下、左→右，符合自然阅读顺序，无需 `setTabOrder` 重排）
Preview Dialog：内容 → 取消 → 开始整理（左→右，符合 §10）
Undo Dialog：内容 → 取消 → 还原（符合）

### Shift+Tab
反向导航：PASS（Qt 原生支持，无焦点丢失/跳窗/不可见控件/循环异常）

## 7. Default Button
Preview: 开始整理 = Default ✅
Undo: 还原 = Default ✅
Welcome: 开始使用 = Default ✅（新补）

## 8. Semantic Safety
Undo ≠ Danger: PASS（全链路 undo-cta；Danger 按钮实例 = 0）
Enter 不触发错误动作: PASS（Enter 仅指向主行动：开始整理/开始使用/还原）
Escape 不触发强操作: PASS（Escape 仅走弱操作：取消/关闭）

## 9. Problems
NONE（无 P0 / 无 P1）

## 10. P2 Notes
- P2-1（UI-1.2.5 已知）→ **本阶段已修复**：Preview/Welcome 主按钮缺 `setDefault`。
- P2-A（UI-1.2.4 已知，薄间隙）：Tertiary 与 Ghost 在 idle 态仅差字重，hover 态已拉开；保持记录，归属 UI-1.3 收口，本阶段不改（避免扩大范围）。
- Accepted Note：`about.py` 单按钮「关闭」=Primary、`custom_page` 休眠页 2 Primary 仍为已接受状态，不扩大。
- Focus ring 渲染依赖 Qt `outline` 属性：在 Windows（Fusion/WindowsVista 风格）下可正常绘制；若极老环境不绘制，回退方案为 focus 态改 `border` 颜色高亮（宽度不变）。当前按标准实现，记为条件风险。

## 11. Tests
compileall: PASS
test_core: PASS
test_security: PASS
test_reliability: PASS
test_windows_paths: PASS
test_p2_coverage: PASS

Headless 渲染校验（Light+Dark）：focus ring 存在且无未替换 token；6 变体 pressed 齐全；3 处调用处修复静态确认通过；Undo dialog 默认语义确认。

## 12. Risk
低。仅 3 行 UI 调用处改动（2×setDefault + 1×setToolTip），无布局/逻辑/业务变化；未触碰禁改区。唯一条件风险为 §10 所述 focus ring 渲染回退（不影响功能，仅焦点可见性）。

## 13. Final Verdict
**PASS**
（Button System 的 Focus / Pressed / Keyboard / Enter / Escape / Tab / Default 交互层完整，语义安全，无 P0/P1，未扩大范围。）

## 14. Next Stage
**UI-1.2.7 — Dialog Interaction Review**

完成后立即停止，不得自动进入 UI-1.2.7。
