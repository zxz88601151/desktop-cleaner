# Desktop Cleaner — UI Refinement Plan（精修计划）

> 阶段：UI Final Polish & Freeze Audit — Phase 2（计划，未实施）
> 生成时间：2026-08-28
> 原则：**仅 UI/UX/视觉层**；不改 `core/data` 业务逻辑、不改数据库、不改测试。
> 分级：P0 严重影响体验 / P1 明显影响专业度 / P2 纯视觉微调。
> 本轮只产出计划，**等待确认后再实施**。

---

## 总目标（§5/§36）

> 一个真正成熟的 Windows 桌面效率工具：少一点、快一点、清楚一点、安全一点。
> 打开 → 选择文件夹 → 扫描 → 确认 → 完成。不用学习、不用思考、不用看说明书。

---

## P0 — 必须改（严重影响体验）

### P0-1 首页第一焦点改为"整理文件"（§6/§8）
- **问题**：`DashboardPage` 把「电脑整洁度」环(240px)+百分比作为第一视觉焦点，主操作被压在下方的次要位置。
- **修改（UI-only，`src/ui/pages/dashboard_page.py`）**：
  - 顶部 Hero 区：大标题「整理你的文件」+ 副标题「让文件回到它们该在的位置」+ 主按钮 **[ 选择文件夹 ]**（Primary，固定高 ~52px）。
  - 点击「选择文件夹」→ `QFileDialog` 选目录 → 写入 `settings_repo.last_source` → `navigate.emit("organize")`（organize 页加载该路径，用户立即看到"当前路径 + 开始扫描"）。
  - 「电脑整洁度」环**降级**为 Hero 右侧或下方的小号次要元素（size 降到 ~120px，或改为一行轻量徽标），不再做第一焦点。
  - 下方保留 Dashboard 统计卡（§17 已符合，作为辅助信息）。
- **验收**：打开软件 3 秒内理解"选文件夹整理"；整洁度环不压过主操作。

### P0-2 首页直接显示"当前路径 + 预计扫描"（§9）
- **问题**：首页无路径/预计信息，必须进 organize 页才看到。
- **修改（`dashboard_page.py`）**：Hero 下方若 `last_source` 存在且为目录，显示「📁 {路径}」+ 轻量说明「点击开始整理即可扫描该文件夹」，与「选择文件夹」并列。
- **验收**：用户首页即知"将整理哪个文件夹"。

---

## P1 — 应改（明显影响专业度/清晰度）

### P1-1 建立按钮三级视觉层级（§7）
- **问题**：organize 页「选择文件夹/开始扫描/生成整理方案」全 `#primary`；完成页按钮混用无层级。
- **修改（`themes.py` QSS + 各页 objectName）**：
  - **Primary**（唯一主行动）：首页[选择文件夹]、organize[开始扫描]、Preview[开始整理]、done[返回首页]。
  - **Secondary**（普通实心/描边）：organize[选择文件夹]浏览、[生成整理方案]→合并后取消、history[返回首页]等。
  - **Tertiary/Ghost**（文字/弱）：[查看历史][再整理一次][取消][关于]。
  - 新增 `#secondary` QSS（accent 描边、白底），区分于 `#primary`（实心）。
- **验收**：每页有且仅有一个最显眼主按钮；用户一眼分辨主次。

### P1-2 精简整理流程（扫描即预览，一步确认）（§11/§36）
- **问题**：「开始扫描」→（页面内分类预览）→「生成整理方案」→（PreviewReportDialog 确认）两步重复预览。
- **修改（`organize_page.py`）**：扫描完成直接弹 `PreviewReportDialog`（即"即将发生什么"），移除页面内"生成整理方案"中间按钮；或页面内直接渲染完整预览 + 「开始整理」。消除冗余一步。
- **验收**：选文件夹 → 扫描 → 确认 → 完成，无重复预览步骤。

### P1-3 Preview 分类卡片化 + 显示"收哪些文件"（§11/§12）
- **问题**：`PreviewReportDialog` 密集表格，未显示分类扩展名范围。
- **修改（`preview_report.py`，UI-only，只读 `core.rules.DEFAULT_RULES` 反向映射 ext→分类，不改成规则）：
  - 分类区改为卡片行：「{emoji} {分类名} — {count} 个 · 收 {jpg, png, gif…}」样式（§12 示例）。
  - 保留"不删除/不覆盖/可撤销"底部三行 + [开始整理]/[取消]。
  - 移动明细列表保留为可折叠"查看详情"。
- **验收**：预览一眼读懂"每类收什么、共多少"；不强制改名（改名越界 core，见下"不实施"）。

### P1-4 History 撤销按钮去危险红（§15/§17）
- **问题**：`HistoryPage._undo_btn` 用 `#danger` 红，暗示破坏性，但撤销是安全可逆。
- **修改（`history_page.py` + `themes.py`）**：改为次级/普通样式（非红），保留二次确认弹窗（`ConfirmUndoDialog` 已是安全门）。撤销=Secondary 层级。
- **验收**：撤销按钮不引发"会删文件"的误判。

### P1-5 移除冗余"整理方案"页（§8）
- **问题**：Sidebar「智能整理」与「整理方案」入口 + 功能重复（CustomPage 的 mode/recursive/文件夹 在 OrganizePage 顶部已存在）。
- **修改（UI-only：`app_shell.py` / `widgets/sidebar.py` / `pages/custom_page.py`）：
  - 从 Sidebar `_NAV` 与 `AppShell._pages` 移除 `custom`；`CustomPage` 可删除或留作内部复用。
  - 导航收敛为：首页 / 智能整理 / 整理历史 / 设置（4 项，更清晰）。
- **验收**：单一核心整理入口，无"该点哪个"困惑。（可逆；如你希望保留预设概念，可改为 organize 页内的高级折叠区，不在本计划。）

### P1-6 设最小窗口尺寸 + 验证响应式（§27）
- **问题**：`AppShell` 无 `setMinimumSize`，缩太小布局重叠/截断。
- **修改（`app_shell.py`）**：`setMinimumSize(900, 620)`；逐页验证 900×620 / 1080×760 / 大窗口下无截断、无按钮消失、无重叠。
- **验收**：最小尺寸下所有页面可用；文字/按钮不溢出。

### P1-7 内联硬编码样式迁移到 Token（§20）
- **问题**：多处 `setStyleSheet` 写死颜色/圆角，绕过统一 QSS，主题切换可能不一致。
- **修改（各页 + `themes.py`）：
  - `dashboard_page` 问候语：改用 `#page-sub` / 新增 `#greet` token，去掉 `#111827` 写死。
  - `organize_page` CTA：`font-size/border-radius` 入 token（新增 `#cta` 或复用 `#primary` + 尺寸约定）；分类名颜色改用 QSS `#cat-name`（已在模板，移除 `THEME_TEXT()` 内联）。
  - `history_page` icon 字号入 `#tl-ico` token。
  - `sidebar` 品牌 mark 渐变改用 `accent` token（或保留小蓝渐变但统一变量）。
- **验收**：主题切换时所有元素一致；无散落硬编码色值。

---

## P2 — 纯视觉微调（可改）

### P2-2 About 署名（§19）
- `version.py` 的 `AUTHOR` 由"个人开发者"改为"© 中哥"（产品身份文案，非业务/数据逻辑，允许）。About 底部显示「© 中哥 All Rights Reserved」。

### P2-3 Welcome 文案对齐 §18
- `welcome.py` bullets 补充「整理前可预览」「不会覆盖已有文件」两条，贴合 §18 四安全点。

### P2-4 History 信息丰富度（§16）
- `history_page.py`：标题改为相对时间「今天 19:42 / 昨天 / 日期」；副标题加源路径「D:\Downloads」。

### P2-5 DPI 属性（§28）
- `main.py` 入口加 `QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)`（PySide6 默认开，但显式声明更稳）+ `setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)`；真实 EXE 在 125%/150% 验证字体/按钮/间距无严重错位。

### P2-6 完成页分类统计（§14）
- `organize_page.py` done stage 增加一行「📸 12  📝 8  🎬 6  🎧 5  📦 3  📁 3」分类数字（数据来自本次 `OrganizeResult.by_category`，UI 层已有）。

### P2-7 问候语随时间（可选）
- `dashboard_page.py` 问候语按当前时段生成「早上好/下午好/晚上好」，去掉写死"早上好"。

---

## 明确不实施（越界/反目标）

- ❌ **分类显示名改名（图片→视觉素材 等）**：`CATEGORY_NAMES` 在 `core/rules.py`，改它越界 RULE-0。§12 的"有趣名称"以 **P1-3 的"显示收哪些文件(扩展名)"** 满足，不强行改名（改名还会导致 history/undo 显示名不一致）。
- ❌ 任何 `core/data` 逻辑、数据库结构、测试逻辑。
- ❌ 架构重构（QWidget→QMainWindow、换框架、WebView/React 等）—— 违反 §二。
- ❌ 玻璃拟态 / 大面积渐变 / 过度阴影 / 炫酷动画 / 装饰图表 / 无意义数字 —— 违反 §30。
- ❌ 移除已验证的安全语义（Preview 确认门、Undo 二次确认、只移动不删除）。

---

## 实施顺序（确认后）

1. **P0-1 + P0-2**：重构 `DashboardPage` Hero（最大改动，先做）。
2. **P1-7**：先把硬编码样式收口到 token（为后续改样式打基础）。
3. **P1-1 + P1-4**：按钮层级 + History 撤销去红。
4. **P1-2 + P1-3**：整理流程精简 + Preview 卡片化。
5. **P1-5 + P1-6**：导航收敛 + 最小尺寸。
6. **P2-2~P2-7**：纯微调。
7. **回归**（§33）：跑 `test_core / test_security / test_reliability / test_windows_paths / test_p2_coverage` + `compileall`；UI 启动成功。
8. **真实 EXE 验证**（§34）：`pyinstaller build.spec` 重建 → 真实 EXE 走查 首页/选目录/扫描/Preview/整理/完成/History/Undo/Welcome/About。
9. **冻结**（§35）：输出 `UI_FINAL_AUDIT.md` + `UI_FREEZE.md`，标记 UI = FROZEN。

---

## 风险与边界

- 所有改动限 `src/ui/`、`main.py` 入口、`version.py` 文案；不动 `src/core/`、`src/data/`、测试。
- P1-5 删页为导航结构改动（UI-only，可逆）；若你倾向保留"整理方案"概念，可改为 organize 页内高级折叠，不删页。
- 真实 EXE 重建须在本机无遗留 `DesktopCleaner.exe` 锁定时产出 `dist/`（参见 PHASE5_RC_REPORT.md §9-C）；否则仍输出 `dist_rc/`。
