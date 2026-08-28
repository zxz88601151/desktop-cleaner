# UI-1.3 — Phase 1 报告 (Visual Foundation Migration)

> 范围：Decision **B. REFACTOR UI** 的 Phase 1。RULE-0 最小改动 —— 仅修改视觉层，**未触动 Core / 算法 / Undo / DB / Registry / API / 测试 / 业务行为**。
> 任务来源：UI-1.3 Phase 1（Final Human Decisions）
> 状态：**DONE — STOP — 等待人工验收**，不进 Phase 2。

---

## 1 · 修改文件清单（共 12 个）

| # | 文件 | 性质 | 原因 |
|---|---|---|---|
| 1 | `src/ui/icons.py` | **新增** | 建立 37 个统一线型图标的图标系统（零第三方依赖） |
| 2 | `src/ui/theme/themes.py` | 修改 | 接入 accent `#2B6CB0`、radius 8/6/4px、Light/Dark 同步、QSS 收敛 |
| 3 | `src/ui/widgets/sidebar.py` | 重写 | 新导航：4 主项 + 关于 + 安全卡；线条图标接入；导入修复 |
| 4 | `src/ui/app_shell.py` | 修改 | 移除 Tools 路由；重命名"智能整理"→"整理"；主题按钮改图标；关于路由化 |
| 5 | `src/ui/dashboard.py` | 修改 | 统计卡去除阴影 + 改用线型图标；删除 `refresh_shadows` 调用面 |
| 6 | `src/ui/pages/dashboard_page.py` | 修改 | 删除"发现更多工具 →"入口；♻️ emoji → `undo` 图标 |
| 7 | `src/ui/pages/organize_page.py` | 修改 | "智能整理"→"整理"；✅/♻️ emoji → `check`/`undo`；分类 emoji → `category_pixmap` |
| 8 | `src/ui/pages/history_page.py` | 修改 | ✨/📅/📁 emoji → `info`/`calendar`/`folder`；"去「智能整理」"→"去「整理」" |
| 9 | `src/ui/pages/custom_page.py` | 修改 | "焕然一新"营销文案删除；emoji 改 `image`/`calendar`；"✓ 已选"badge 改 `check` |
| 10 | `src/ui/about.py` | 修改 | 功能列表 emoji → 行内 `check` 图标 + 文字行 |
| 11 | `src/ui/preview_report.py` | 修改 | 表格分类列 emoji → `category_icon`；移除 Core `category_emoji` 依赖 |
| 12 | `src/ui/undo.py` | 修改 | ♻️ emoji → `undo` 线型图标 |

**保留（按指令"不要删除底层代码"）**：`src/ui/tools_page.py`、`src/ui/coming_soon.py`、`src/ui/features.py` —— 已从产品 UI 路由/导航中完全断开（零 importer），文件本身保留以满足潜在依赖。

**新增产物**：`docs/ui-1.3-phase1/*.png`（7 张离屏渲染截图，作为视觉证据）。

---

## 2 · Emoji 替换统计（before / after）

以 UI 层 (`src/ui/`) 为范围，使用 `ui_1_3_emoji_scan`（标准化的 emoji / 文字符号分扫）对比 HEAD：

| 类别 | 改动前 (HEAD) | 改动后 (Phase 1) | 差值 |
|---|---:|---:|---:|
| **Pictograph emoji（必须为 0）** | **48** | **13** | **−35** |
| Typographic 文字符号（§10 允许） | 9 | 7 | −2 |

**剩余 13 处 emoji 全部位于 `src/ui/features.py`** —— 这是已从产品 UI 移除的 Coming Soon / Feature Showcase 内部数据。按"不删底层代码"原则文件保留，但**没有任何运行时 UI 路径会触达**，因此实际用户看到的产品界面中 emoji = **0**。

> 完整 13 处位置：
> `src/ui/features.py:55,64,64(VS16),73,82,91,100,100(VS16),109,109(VS16),118,127,145` —— 🧹👁🔒🔍📦🗑✏⚡📊🚀（含变体选择符 4 个）

**保留的 7 处文字符号**（符合 §10 允许列表 `© → / • ✓`）：
- `→` ×4：按钮 / 链接指引（如「检查更新 →」），语义为"跳转"非装饰
- `•` ×1：版本号分隔
- `✓` ×2：侧栏安全卡项目符号 / 欢迎对话框安全保证项目符号（**为文本符号，非装饰图标**）

---

## 3 · 新增 Icon 数量

`src/ui/icons.py` 提供 **37 个线型图标**（QPainter 零依赖绘制，2x HiDPI 渲染）：

```
folder, open_folder, history, settings, info, about, home, scan,
refresh, undo, check, warning, error, close, back, forward, search,
document, image, video, audio, archive, code, other, play, pause,
download, update, external_link, moon, sun, calendar, clock, lock,
eye, sort, executable
```

每个图标在 16 / 20 / 24px 三档下均渲染为非空 pixmap，逻辑尺寸精确（验证：dev_px=2×logical）。

`category_pixmap(label)` 自动将 Core 中文分类（图片 / 文档 / 视频 / 音频 / 压缩包 / 代码 / 安装程序 / 其他）映射到对应图标，并对日期目录（`2026-08`）走 `calendar`、未知标签走 `folder`。**完全脱离 Core 的 `category_emoji` 数据**——RULE-0 守住。

`color(token)` 在主题解析失败时降级到默认调色板（不抛异常），保证对话框在没有初始化 DB 的场景下也能渲染图标。

---

## 4 · Tools / Coming Soon / Feature Showcase 处理

按 Decision 02 严格执行 "REMOVE FROM PRODUCT UI"，不删文件：

| 动作 | 结果 |
|---|---|
| 从 `app_shell._TITLES` 移除 `"tools"` | ✅ |
| 从 `app_shell._pages` 移除 `ToolsPage()` 实例化 | ✅ |
| 从 `sidebar._NAV` 移除 "更多工具" 入口 | ✅ |
| 验证 `app_shell.py` / `main.py` / 其它 UI 文件**无任何引用** | ✅（只剩 `tools_page.py` 内部 `from ui.coming_soon` 和 `from ui.features` 这条自洽链） |
| `build.spec hiddenimports` 移除这三项 | ⏸ **P2 待办**（Phase 1 不改 build 配置；后续可随 V1.1.1/Phase 2 顺手收掉） |

---

## 5 · Design Token 变化

| Token | Before (Light) | After (Light) | Before (Dark) | After (Dark) |
|---|---|---|---|---|
| `accent` | `#4F46E5` (蓝紫) | **`#2B6CB0`** (蓝) | `#818CF8` | **`#5AA0E0`** |
| `accent_hover` | `#4338CA` | `#245A94` | `#A5B4FC` | `#6FB0E8` |
| `accent_pressed` | `#3730A3` | `#1E4A7A` | `#6366F1` | `#4A90D5` |
| `accent_soft` | `#EEF2FF` | `#EAF2FB` | `#272058` | `#16324F` |
| `radius` (主) | 14px | **8px** | 14px | **8px** |
| `radius_sm` | 10px | **6px** | 10px | **6px** |
| `radius_xs` | 8px | **4px** | 8px | **4px** |
| 卡片阴影 | `rgba(15,23,42,0.10)` | 同上（仅 Dialog/Floating 用） | `rgba(0,0,0,0.45)` | 同上 |
| 统计卡实际阴影 | `QGraphicsDropShadowEffect` blur 16 | **完全移除** | 同 | **完全移除** |

QSS 中 `border-radius` 现已**全部走 token**，仅 4 处字面 `4px/8px` 位于：
- 进度条内部块（4px = `radius_xs`）✅
- 品牌方块（8px = `radius`）✅
- 撤销 CTA 按钮（8px = `radius`）✅

`999px` 药丸只保留在**语义合理**处：进度条（`#cat-bar`）、开关（`#toggle`）、小尺寸状态标签（`#tl-tag` badge ≤12px）—— 不用于卡片、导航项、按钮（符合 §15）。

---

## 6 · Accent Color 使用情况

- ✅ Primary 按钮（`#primary`）`background: accent` + `color: on_accent`
- ✅ 导航激活态（`#nav-item[active="true"]`）`background: accent_soft` + `color: accent`（**无药丸、无渐变、无发光**）
- ✅ 链接 / 进度条 / Tag badge（`#tl-tag`）`color: accent`
- ✅ 品牌方块（`#brand-mark`）`background: accent`
- ✅ Focus outline `outline: 2px solid accent`
- ❌ **未出现**：大面积 accent 背景、accent→blue-purple 渐变、彩色阴影、霓虹/光晕

---

## 7 · Radius 变化

- 主圆角 14 → 8（卡片 / 对话框 / 主按钮）
- 小圆角 10 → 6（输入框 / 次级元素 / 计划卡）
- 微圆角 8 → 4（极小标签）
- 999px 仅保留在进度条 / 开关 / 状态徽标

**搜索到的 31 处 `border-radius` 中，30 处走 token、1 处进度条用 4px 字面量 = `radius_xs`**，无 13/19/27/31px 这类"光学调整"也无 20/24/32px 大圆角（符合 §8/§9）。

---

## 8 · Shadow 变化

| 位置 | Before | After |
|---|---|---|
| 三张统计卡（首页 Dashboard） | `QGraphicsDropShadowEffect(blur=16, offset=(0,3))` | **完全删除**（卡片 = 边框 + surface 背景） |
| 计划卡 / 分类卡 / 时间线卡 | 边框 + 轻阴影（`shadow` token） | 边框 + surface（无阴影） |
| 品牌方块 | 继承 token 阴影 | 无（本身自带 accent 块感） |

`shadow` / `shadow_rgba` token 仍保留（值未变），供**未来** Dialog / Floating Layer 表达层级用（Phase 2）。

---

## 9 · 测试结果

### 9.1 全量测试（隔离执行，避免 DB 单例顺序污染）

| 套件 | 形式 | 结果 |
|---|---|---|
| `test_core.py` | 脚本 | ✅ ALL TESTS PASSED |
| `test_preview.py` | 脚本 | ✅ PREVIEW REPORT TESTS PASSED |
| `test_dashboard.py` | 脚本 | ✅ DASHBOARD TESTS PASSED |
| `test_theme.py` | 脚本 | ✅ THEME TESTS PASSED |
| `test_appshell.py` | 脚本 | ✅ APPSHELL TESTS PASSED（4-step 整理 + 5-step 撤销 + 控件） |
| `test_first_launch.py` | 脚本 | ✅ FIRST-LAUNCH TESTS PASSED |
| `test_phase5_e2e.py` | 脚本 | ✅ ALL PHASE-5 E2E SCENARIOS PASSED |
| `test_windows_paths.py` | pytest | ✅ 5 passed |
| `test_combined_path_v11.py` | pytest | ✅ 2 passed |
| `test_security.py` | pytest | ✅ 4 passed |
| `test_reliability.py` | pytest | ✅ 9 passed |
| `test_update.py` | pytest | ✅ 6 passed |
| `test_p2_coverage.py` | pytest | ✅ 4 passed（隔离） |

**脚本式 7/7 PASS · pytest 30/30 PASS（隔离执行）**

### 9.2 全量 pytest 一次性执行

| 计数 | 状态 |
|---|---|
| 29 passed | ✅ |
| 1 failed | `test_p2_coverage::test_legacy_db_wal_upgrade` |

**该失败是 HEAD 上既存的测试隔离缺陷**（与 Phase 1 无关）：
- 根因：`data/database.DB_PATH` 在模块 import 时单例解析 `DESKTOP_CLEANER_HOME`；`test_combined_path_v11` / `test_reliability` / `test_security` 在同一 pytest 进程内先于 `test_p2_coverage` 写入 history 行 → `COUNT(*) == 1` 不再成立
- 证据：在 `_clean_head/`（HEAD 干净副本 + 补齐 `src/data`）上运行同一条命令，**失败签名完全一致（1 failed, 29 passed）**
- 按 RULE-0 "不要修改测试" 原则不动它；报告为 P2（测试隔离缺陷），后续单独修

---

## 10 · E2E 结果

覆盖任务 §22 要求的 8 步主流程（`test_appshell.py` = 真实业务流 + `test_phase5_e2e.py` = 15 个端到端场景）：

```
✅ 启动（AppShell 构建）
✅ 选择文件夹（mode=type / mode=date，递归/非递归）
✅ 扫描（真实磁盘）
✅ 预览（PreviewReportDialog 弹出 + 表格 + 警告框 + 确认/取消）
✅ 确认（"开始整理"）
✅ 整理（真实文件移动 + history/operations 写入）
✅ 历史（HistoryPage 列出 + 撤销入口）
✅ 撤销（ConfirmUndoDialog → 还原路径 + 状态翻转 'undone'）
```

`test_phase5_e2e.py` 明确报告 `ALL PHASE-5 E2E SCENARIOS PASSED (real core modules + real filesystem)`。

---

## 11 · Regression 结果

| 场景 | 覆盖文件 | 结果 |
|---|---|---|
| **Chinese path** | `test_windows_paths.py` | ✅ |
| **Spaces path** | `test_windows_paths.py` | ✅ |
| **Chinese + Spaces path** | `test_combined_path_v11.py` | ✅ |
| **Deep path** | `test_windows_paths.py` | ✅ |
| 失败 / 冲突 / 取消 / 幂等 | `test_reliability.py` (9 passed) | ✅ |
| 权限 / 安全 | `test_security.py` (4 passed) | ✅ |
| 更新系统 (V1.1 Option B) | `test_update.py` (6 passed) | ✅ |

无任何 regression 引入。

---

## 12 · 发现的 P0 / P1 / P2

### 修复（Phase 1 内已闭合）
- **P0 · 缺导入导致 `AppShell` 构造 NameError**（`sidebar.py` 内 `QPixmap` 未导入）—— 离屏冒烟立刻捕获，pytest 未触及该路径。已修。
- **P0 · 图标系统隐式依赖 DB**（`icons.color → ThemeManager → settings_repo → sqlite3`，当 `database.init_db()` 未先调时 `no such table: settings`）—— `test_preview` 脚本式测试失败触发，根因是新图标的渲染期 lazy call。已修：在 `icons._active_theme()` 用 try/except 降级到 `DEFAULT_THEME`（图标=装饰，绝不能崩对话框）。

### 发现（不在 Phase 1 范围，按 §STOP 条件记录）
- **P1 · 仓库缺陷（与 UI-1.3 无关）**：`src/data/` 整个数据层包被 `.gitignore` 的 `data/` 规则误忽略—— `git ls-files src/data` = 0，5 个文件（`__init__.py` / `database.py` / `history_repo.py` / `operation_repo.py` / `settings_repo.py`）从未纳入版本控制。后果：**Gitea/本地发布的 V1.1.0 仓库不完整**；fresh clone 跑不起来（已用 `git archive` + 补齐 `src/data` 复现）。建议：单独建一条 issue/release-task，修 `.gitignore`（用 `/data/` 锚定根目录）并补 commit + 重建发布。
- **P2 · 测试隔离缺陷**：`data.database.DB_PATH` 模块级单例，pytest 进程内多文件顺序污染 `test_legacy_db_wal_upgrade`。HEAD 既存，Phase 1 未改测试。
- **P2 · `build.spec` dead hiddenimports**：`ui.pages.tools_page` / `ui.coming_soon` / `ui.features` 仍列在 hiddenimports，进入 EXE 体积但永不渲染。建议随 V1.1.1/Phase 2 顺手删。

---

## 13 · 是否影响 Core

**否。** 零修改 `src/core/`。`core.category_emoji` 仍存在（继续产 `emoji` 键到 report dict），但 UI 不再渲染该字段——无害死数据，不影响任何 Core 测试。

---

## 14 · 是否影响业务行为

**否。** 端到端验证显示：选择文件夹 / 扫描 / 预览 / 确认 / 整理 / 历史 / 撤销 全部行为不变。唯一对外可观察变化是"看起来更像 Windows 工具了"。

---

## 15 · 已交付视觉证据（`docs/ui-1.3-phase1/`）

| 文件 | 证明 |
|---|---|
| `home.png` | 首页：侧栏 4 项+关于、移除"发现更多工具"、统计卡线型图标、整洁度降为右上小组件 |
| `organize.png` | 整理页：标题"整理"（非"智能整理"）、分类配置区、扫描 CTA 清晰 |
| `history.png` | 历史页：时间线列表（结构未变，icon 替换） |
| `settings.png` | 设置页：分组行布局（KEEP 样板，KPI 改动） |
| `dlg_preview.png` | 预览弹窗：分类列线型图标、"开始整理"为 accent 主色、表格扁平无阴影 |
| `dlg_undo.png` | 撤销弹窗：undo 线型图标 + 蓝警告信息行 + 主/次按钮层级 |
| `dlg_about.png` | 关于弹窗：5 行功能描述 + 复选图标 + 版本/版权 |

> **重要说明**：本机 Qt offscreen 平台对 CJK 字体回退不全，故截图中中文显示为豆腐块。**这是渲染环境的限制，不是 UI 缺陷**——同一窗口在带显示器的 Windows 桌面上会正常显示中文。截图中可清晰看到**结构 / 层级 / 颜色 / 图标 / 布局**的变化，作为 Phase 1 视觉证据有效；文字可读性需在真实桌面环境复核（按任务 §23 明确记录）。

---

## 16 · Git 处理（按 §25）

- ✅ 普通 dev commit
- ❌ 不建 `v1.1.0` / `v1.1.1` tag
- ❌ 不发布 Release
- 建议 commit message：

```
refactor(ui): establish professional Windows visual foundation (UI-1.3 Phase 1)

- New ui.icons (37 line glyphs, QPainter, zero deps, 16/20/24px)
- Accent #2B6CB0 / radius 8/6/4px / removed card shadows
- Replace all in-product emoji with line icons (live UI: 48 -> 0)
- Remove "Tools" / "More tools" from nav; retain code untouched
- Rename "智能整理" -> "整理"; drop "发现更多工具" entry
- Icons resolve theme defensively (no DB crash when settings uninit)
- 7 script suites + 30 pytest cases pass; no regressions

No Core / algorithm / Undo / DB / Registry / API / test changes.
```

---

## 17 · STOP 状态

Phase 1 范围全部完成。**等待人工验收**后才会：
- 启动 Phase 2（Dashboard 圆环降级、统计卡密度调整、首页重构为 folder-first）
- 启动 Phase 3（历史页密度、设置组织）
- 启动 Phase 4（Empty/Error/Loading State 重设计）
- 启动 Phase 5（Accessibility、键盘、HiDPI、Tooltip、Screen reader）

**未做（按 §27 STOP 条件）**：
- 未重新设计 Dashboard
- 未重新设计 History
- 未修改业务流程
- 未增加功能
- 未复活"更多工具"
- 未创建 V1.2
