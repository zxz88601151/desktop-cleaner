# UI-1.1 — Design Token Audit + Minimal Fix

> UI-1 第 1 个子阶段。本阶段**只做 Design Token 审计 + 最小修复**，未进入 Button/Card/Typography/Theme/Nav/DPI 阶段，未实现任何新功能、未碰禁改区。

---

## 【阶段】
UI-1.1 / Design Token Audit + Minimal Fix（UI-1 子阶段 1 / 8）

## 【修改文件】
| 文件 | 改动 |
|------|------|
| `src/ui/theme/themes.py` | `#badge` 的 `color: #FFFFFF` → `color: {on_accent}`（P2） |
| `src/version.py` | 新增品牌/法务 token `COPYRIGHT_TEXT = "© 中哥 All Rights Reserved"`（P1） |
| `src/ui/about.py` | 导入 `COPYRIGHT_TEXT`，作者行由 `f"{AUTHOR} · All Rights Reserved"` 改为 `COPYRIGHT_TEXT`（P1，去掉 `·` 变体） |

## 【修改内容】
1. **P2 — `#badge` 硬编码颜色 token 化**：原 `color: #FFFFFF` 改为 `color: {on_accent}`。浅色主题 `on_accent=#FFFFFF`、深色 `on_accent=#0B1120`，徽章文字色随主题正确切换，不再写死白色。
2. **P1 — 版权文案逐字统一**：在 `version.py` 建立唯一常量 `COPYRIGHT_TEXT`，`about.py` 引用它。消除 "© 中哥 · All Rights Reserved" 这一非逐字变体。

## 【未修改内容】
- **未新建 token 集**：Section 4 目标中的 `surface_elevated`/`border_subtle`/`warning`/`disabled` 未新增。原因：指令要求"优先保留已有命名，不要重复创建另一套 token"。现有命名可直接承接目标表（见下方映射），新增只会制造第二套体系。
- **Typography scale 未建**：`display/title/heading/body/body_small/caption/button/metric` 当前是各组件内联字号，归 **UI-1.4**。
- **Spacing token 未引**：`4/8/12/16/20/24/32/40` 当前为内联魔法数，归 **UI-1.4/UI-1.5**。
- **Tertiary button 未加**：`#tertiary` 缺失，归 **UI-1.2**。
- **`sidebar.py:128` 白色 logo 字形**：`QColor("#FFFFFF")` 是画在 `brand-mark`（背景恒为 `accent`）上的 logo 图标。白字在浅色/深色双主题下均正确（accent 在双主题均为靛蓝调），属主题稳定、有意的图标色，**非设计系统 token 违规**，保留。
- **Legacy shim**（`ui/themes.py`、`ui/theme_manager.py`、`ui/styles.py`）未动，15+ 模块依赖。
- **禁改区**（`core/*`、`data/*`、`ui/undo.py`、`ui/state/worker.py`、`utils/*`）未动。

## 【测试结果】
- `python -m compileall -q src main.py` → **PASS**
- `test_core.py` / `test_security.py` / `test_reliability.py` / `test_windows_paths.py` / `test_p2_coverage.py` → **全部 PASS**

## 【视觉验证】
- Headless 渲染校验（light + dark）：两者均无未替换的 `{token}` 残留。
- Dark 主题 `#badge` 渲染为 `color: #0B1120`，证明已走 token（非写死 `#FFFFFF`）；light 为 `#FFFFFF`（来自 token，非字面量）。
- `COPYRIGHT_TEXT` 校验为 `'© 中哥 All Rights Reserved'`（逐字）。
- 像素级 GUI 目视（主题切换观感、DPI）无法 headless 验证，留待 UI-1.5/UI-1.7 人工确认。

## 【风险】
- **极低**：仅 token 重指向 + 文案常量，无布局/逻辑/数据流变化。
- **verbatim 空格提示（需你确认）**：本次 P1 按你给的 `© 中哥 All Rights Reserved`（单空格）实现；而初始审计文档写的是 `© 中哥  All Rights Reserved`（双空格）。两者冲突。若你需要双空格，告知我立即改。
- **底部版权**：当前项目**没有**底部状态栏版权（Section 11 提到的 bottom status 位置尚未实现）。建议后续阶段（UI-1.6/UI-1.7）统一加入并复用 `COPYRIGHT_TEXT`。

---

## Design Token 审计报告（现有体系 → 目标表映射）

现有 token 已集中在 `src/ui/theme/themes.py`（`LIGHT`/`DARK` 调色板 + 单一 `QSS_TEMPLATE` + `build_stylesheet()` 替换）。结论：**地基扎实，无需推翻，仅收口**。

### Color（现有 → 目标）
| 目标 token | 现有命名 | 状态 |
|-----------|----------|------|
| background | `bg` | ✓ 已有 |
| surface | `surface` | ✓ 已有 |
| surface_elevated | `surface_alt` | ✓ 复用（不新建） |
| border | `border` | ✓ 已有 |
| border_subtle | `border` | ✓ 复用（`border` 本就偏淡；`border_strong` 为强档） |
| text_primary | `text` | ✓ 已有 |
| text_secondary | `text_secondary` | ✓ 已有 |
| text_muted | `text_muted` | ✓ 已有 |
| accent | `accent` | ✓ 已有 |
| accent_hover | `accent_hover` | ✓ 已有 |
| accent_pressed | `accent_pressed` | ✓ 已有 |
| success | `success` | ✓ 已有 |
| warning | — | ✗ 缺失（当前无任何 warning 状态 UI；建议有 warning 状态时再补，不在本阶段造无用 token） |
| danger | `danger` | ✓ 已有 |
| disabled | — | ✓ 由 `QPushButton:disabled` 用 `text_muted`+`surface_alt`+`border` 表达，无需独立 token |

辅助：`surface_hover`、`accent_soft`、`danger_soft`、`success_soft`、`log_bg`、`log_text`、`separator`、`shadow`、`shadow_rgba`、`radius`/`radius_sm`/`radius_xs`。

### Typography（现状）
- 现状：各组件内联字号（`#title 22/700`、`#page-title 24/700`、`#section-title 14/600`、`#subtitle 12.5`、`#stat-value 24/700`、`#score-v 56/780` 等），**无集中字号阶梯**。
- 结论：归 UI-1.4 建立 `display/title/heading/body/body_small/caption/button/metric` 阶梯并回引，本阶段不动。

### Spacing（现状）
- 现状：布局内联 `padding/spacing/margin`（8/10/11/12/14/16/18/20/22/24 等魔法数）。
- 结论：归 UI-1.4/UI-1.5 引入 `4/8/12/16/20/24/32/40` 间距 token 并回引，本阶段不动。

---

## 【下一阶段】
**UI-1.2 Button System**：补齐 `#tertiary` 按钮档，并统一 `Primary / Secondary / Tertiary / Ghost / Danger / Disabled` 的 `normal / hover / pressed / disabled / :focus` 五态（重点检查 `:pressed`，不能只设计 hover）。完成后停止并汇报，等待确认再进 UI-1.3。

> 按指令，UI-1 完成后停止，**不**自行进入 UI-2（Tools Hub / Feature Registry / Coming Soon）。
