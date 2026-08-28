# Desktop Cleaner — UI Baseline（冻结前快照）

> 阶段：UI Final Polish & Freeze Audit — Phase 1（审计，未改任何代码）
> 生成时间：2026-08-28
> 范围：仅 UI/UX/视觉层（`src/ui/`、`main.py` 入口）。**未修改任何文件**，本文件为修改前的真实状态记录。
> 对照目标：Minimal · Professional · Clean · Fast · Safe · One-click

---

## 1. 当前页面结构（App Shell）

入口 `main.py` → `AppShell`（QWidget，`resize(1080,760)`，无 `setMinimumSize`）。

```
AppShell
├─ Sidebar (固定 240px)        品牌 + 导航 + 安全卡
└─ 右栏
   ├─ TopBar                    页面标题(左) / 关于(ghost) + 主题切换(icon)(右)
   └─ QStackedWidget
      ├─ home       → DashboardPage    首页（整洁度环 + CTA + 统计卡）
      ├─ organize    → OrganizePage     智能整理（选文件夹→扫描→生成方案→确认→完成）
      ├─ custom      → CustomPage       整理方案（选方式+递归+文件夹→开始整理）
      ├─ history     → HistoryPage      整理历史（时间线卡片 + 撤销）
      └─ settings    → SettingsPage     设置（深色/默认方式/子文件夹/关于）
```

首次启动弹 `WelcomeDialog`（一次性，存 `first_launch_completed`）。

对话框：`PreviewReportDialog`（整理前模拟报告，安全门）、`ConfirmUndoDialog`（撤销确认）、`AboutDialog`。
共享：`ui/undo.py`（run_undo + ConfirmUndoDialog）、`ui/state/worker.py`（QThread 后台任务）、`ui/dashboard.py`（StatCard×3）、`ui/widgets/`（sidebar / controls / score_ring）。

---

## 2. 视觉系统（已有，强项）

- **统一 Design Tokens**：`ui/theme/themes.py` 定义 `LIGHT`/`DARK` 调色板 + 单一 token 化 `QSS_TEMPLATE`（字体/圆角/按钮/卡片/输入/对话框/badge/status 全部 token 化）。这是正确的基础，应保留并扩展。
- **颜色（§21 基本符合）**：浅色主背景 `#F4F6FB`（接近白）、卡片 `#FFFFFF`、文字 `#0F172A`、辅助 `#475569`、单一品牌 Accent `#4F46E5`（indigo）；成功绿/错误红语义色。无彩虹色、无大面积渐变（仅 logo 小渐变）。
- **圆角（§22 符合）**：`radius=14px` 轻圆角，button `radius_xs=8px`，不过度圆润。
- **字体**：`"Segoe UI","Microsoft YaHei","PingFang SC"` 13px，统一。
- **动画（§24 符合）**：仅 hover/pressed/loading/success，无复杂动画。
- **图标（§23 基本符合）**：emoji 用于导航/分类/轻量状态，未到处滥用，无 Emoji+Icon 重复。

### 优点小结
1. Token 化 QSS 体系成熟，深浅色主题一致。
2. 错误状态已全链路处理（`worker` → `friendly_message` → `QMessageBox.critical`，不暴露 traceback），符合 §26。
3. Welcome / About / Preview / Undo 安全语义清晰，符合"Safe"目标。
4. Dashboard 统计卡简洁（无大图表），符合 §17。
5. History 用时间线卡片而非数据库表格，符合 §16。
6. 整理/扫描走后台线程，UI 不假死，符合 §10/§13。

---

## 3. 当前问题（按严重度）

### P0 — 严重影响使用体验（必须改）
- **P0-1 首页第一视觉焦点错误（§6/§8）**：`DashboardPage` 把「电脑整洁度」`ScoreRing`(240px) + 百分比作为第一视觉焦点，主操作「✨ 智能整理」反而在其下方。用户打开 3 秒内看到的是"评分环"而非"选文件夹整理"。§6/§8 明确要求首页第一焦点是"整理文件 / 选择文件夹"，Dashboard 必须弱化为辅助信息。
- **P0-2 首页无"选择文件夹"直达（§8/§9）**：首页只有「智能整理」按钮路由到 organize 页，没有在首页直接显示"当前路径 + 预计扫描 + [选择文件夹]/[开始扫描]"的核心整理区。违反 §8/§9 推荐结构。

### P1 — 明显影响专业度/清晰度（应改）
- **P1-1 按钮视觉层级缺失（§7）**：`OrganizePage` 中「选择文件夹」「开始扫描」「生成整理方案」全是 `#primary`（accent 实心），视觉权重相同；完成页 4 个按钮也混用 primary/undo-done(红)/ghost。§7 禁止"所有按钮相同权重"，需建立 Primary/Secondary/Tertiary 三级。
- **P1-2 整理流程步骤冗余（§11/§36）**：organize 页是「开始扫描」→（显示分类预览）→「生成整理方案」→（弹 PreviewReportDialog 确认）→ 移动。扫描与"生成方案"是两步重复预览（页面内预览条 与 弹窗内容重叠），多一步。§11 要求扫描后直接预览"即将发生什么"+「开始整理」一步确认。
- **P1-3 Preview 分类展示不够"一眼懂"且缺扩展名（§11/§12）**：`PreviewReportDialog` 用 `QTableWidget`（分类/目标文件夹/文件数/大小）+ 移动明细列表。§11 示例是卡片式「📸 视觉素材 12 / 📝 工作文档 8 …」；§12 要求"让用户知道这个分类会收哪些文件（JPG/PNG…）"。当前预览未显示分类的扩展名范围，且表格偏密集。
- **P1-4 History 撤销按钮用 danger 红（§15/§17）**：`HistoryPage._undo_btn` 为 `#danger`（红）。撤销是**安全可逆**操作（非删除），红色会让用户误判为危险/破坏性。应降为次级/普通样式。
- **P1-5 导航重复：整理方案页（§8）**：Sidebar 同时存在「智能整理」(organize) 与「整理方案」(custom) 两个几乎相同入口；`CustomPage` 的"方式+递归+文件夹+开始整理"与 `OrganizePage` 顶部已有的"整理方式 Segmented + 包含子文件夹 Toggle"完全重复。两个入口让用户困惑"该点哪个"，增加认知负担。§8 只要求一个核心整理区。
- **P1-6 响应式最小尺寸缺失（§27）**：`AppShell` 仅 `resize(1080,760)`，**未设 `setMinimumSize`**。窗口缩到很小会布局重叠/截断（尤其 organize 页 src_row、自定义页）。需设最小尺寸并验证。
- **P1-7 内联硬编码样式绕过 Token（§20）**：多处用 `setStyleSheet` 写死颜色/圆角，破坏统一 Design Tokens：
  - `dashboard_page` 问候语 `color:#111827`（写死，未用 token）
  - `organize_page` CTA `font-size:17px;border-radius:16px;`（绕开 token radius）；分类名 `color:{text}` 用 `THEME_TEXT()` 函数硬编码
  - `history_page` icon `font-size:22px;` 写死
  - `sidebar` 品牌 mark `qlineargradient(#3B82F6,#2563EB)` 写死（未用 accent token）
  - 应迁移到 QSS tokens，保证主题切换时一致。

### P2 — 纯视觉微调（可改）
- **P2-1 分类 emoji 微调（§12/§23）**：当前 `🖼️📄🎬🎵🗜️💻⚙️📦`；§12 示例偏好 `📸/📝/🎬/🎧/📦`。emoji 当前定义在 `core/rules.py`（`CATEGORY_EMOJI`）——**改它越界 RULE-0**；UI 层覆盖需在 `organize_page`/`preview_report`/`history` 多处同步，且与 undo/history 显示名易不一致，**不建议改名**，仅作 P2 备注。
- **P2-2 About 署名（§19）**：`version.AUTHOR="个人开发者"`，§19 要求底部「© 中哥 All Rights Reserved」。改 `version.py`（产品身份，非业务/数据逻辑，属展示文案）允许，标 P2。
- **P2-3 Welcome 文案对齐 §18**：当前 4 条 bullet 缺"整理前可预览""不会覆盖已有文件"两条（§18 示例强调）。P2。
- **P2-4 History 信息丰富度（§16）**：当前显示 `#id · 日期 / 方式 / 整理 N 个 / 状态 tag`，缺"相对时间(今天 19:42)"与"源路径(D:\Downloads)"。P2。
- **P2-5 DPI 属性（§28）**：`main.py` 未设 `QApplication.setAttribute(AA_EnableHighDpiScaling)` / `setHighDpiScaleFactorRoundingPolicy`。125%/150% 下可能模糊；建议入口加属性（UI 入口层，允许）。P2。
- **P2-6 完成页缺分类统计（§14）**：`OrganizePage` done stage 仅"已移动 N 个文件到分类文件夹"，未列出「📸 12 📝 8 …」分类数字。P2。
- **P2-7 问候语固定"早上好"**：`dashboard_page` 写死"早上好"，不随时间变化。P2。

---

## 4. 状态覆盖审计

| 状态 | 当前实现 | 评价 |
|---|---|---|
| 空状态 | organize hint「选择文件夹后点击开始扫描…」；history「还没有整理记录…」 | ✓ 符合 §25 |
| 加载/扫描 | `QProgressBar` 不确定模式 + status「正在扫描：{root} …」；后台线程不假死 | ✓ 符合 §10；扫描中无实时计数（scan 一次性返回，非强制） |
| 整理执行 | `move_items` 真实 cur/total → 进度条真实百分比 + status | ✓ 符合 §13 |
| 成功 | done stage ✅「整理完成」+ QMessageBox 还原完成 | △ 完成态用弹窗而非页面内；基本符合 §14/§15 |
| 失败 | `_on_error` → `QMessageBox.critical(friendly_message)`；done 页"查看失败明细" | ✓ 符合 §26/§14（明确"N 成功 M 失败"） |
| 撤销中 | status「正在还原本次整理…」 | ✓ 符合 §15 |
| 撤销部分失败 | `QMessageBox.warning` 列出失败文件 | ✓ 符合 §15（应加页面内失败明细入口，P2） |
| 错误 | 全链路友好文案，无 traceback | ✓ 符合 §26 |

---

## 5. 哪些值得改 / 哪些不要改

**值得改（见 UI_REFINEMENT_PLAN.md）**：P0-1、P0-2、P1-1~P1-7、P2 中除 P2-1(改名)外的项。

**不要改（明确排除）**：
- ❌ 任何 `src/core/`、`src/data/` 逻辑：分类规则、移动/扫描/撤销算法、数据库、安全逻辑、路径逻辑、日志逻辑。
- ❌ 分类显示名改名（`CATEGORY_NAMES`）—— 在 `core/rules.py`，越界 RULE-0；§12 的"有趣名称"需求以 UI 层"显示收哪些文件(扩展名)"满足，不强行改名。
- ❌ 数据库结构、业务逻辑、测试逻辑。
- ❌ 架构重构（QWidget→QMainWindow、换框架、引入 WebView/React 等）—— 均违反 §二。
- ❌ 为"看起来做了很多"而做的装饰性修改（玻璃拟态/大面积渐变/过度阴影/炫酷动画/装饰图表）—— 违反 §30。
- ❌ 删除已验证通过的安全语义（Preview 确认门、Undo 二次确认、文件只移动不删除）。

---

## 6. 窗口 / 响应式 / DPI 现状

- 窗口：`resize(1080,760)`，无 `setMinimumSize` → **P1-6**。
- ScrollArea：organize stage、history list 均为 `QScrollArea` + `setWidgetResizable(True)` ✓（长内容可滚动）。
- DPI：未显式设置高 DPI 属性 → **P2-5**（待真实 125%/150% 验证）。
- 字体/按钮/间距：统一 13px + token 间距，缩小窗口时部分固定高度按钮（44/46px）可能拥挤但未溢出。
