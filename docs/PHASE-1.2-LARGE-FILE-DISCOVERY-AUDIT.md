# PHASE 1.2 — LARGE FILE DISCOVERY AUDIT

> 阶段性质：READ-ONLY DISCOVERY + SCOPE LOCK
> 项目：Desktop Cleaner / 桌面文件整理助手
> 产品版本：1.1.1（src/version.py `__version__ == "1.1.1"`）
> 审计时间：2026-09-03（基于真实仓库重采，非历史报告）
> 本阶段唯一写入文件。未修改任何业务代码 / 配置 / UI / 依赖 / 测试。

---

## A. Baseline

实测命令与结果（2026-09-03 重采，不沿用历史报告）：

| 项 | 值 |
|---|---|
| `git branch --show-current` | `main` |
| `git rev-parse HEAD` | `9532e3832a024635e3fd4c1a631bb18ef34409e6`（短 `9532e38`） |
| HEAD subject | `docs: archive phase reports and add project README` |
| `git status --short` | 仅两项未跟踪：`?? docs/PHASE_R5.1_RELEASE_ARTIFACT_SYNC.md`、`?? docs/PHASE_R5_FINAL_RELEASE_AUDIT.md` |
| staged changes | 空（`git diff --cached --stat` 无输出） |
| 版本号 | `src/version.py` `__version__ = "1.1.1"` |

判定：**工作树对本阶段范围 CLEAN**。唯一未跟踪项为历史遗留的 2 个外部 R5 文档（文件名/内容错位，一贯 EXCLUDE，本阶段不触碰、不处理）。无用户未提交改动、无 release artifact 需要避让（dist 产物由 `.gitignore` 管理，未入库）。

---

## B. Current Architecture

基于实际目录扫描与代码读取，真实架构为（与规范假设一致，细节以代码为准）：

```
main.py                       —— 入口：init_db -> reconcile_pending -> AppShell.show
  └─ ui/app_shell.py          —— AppShell：Sidebar(240px) + TopBar + QStackedWidget 路由
       ├─ ui/pages/organize_page.py   整理（Product Home，默认落地页）
       ├─ ui/pages/dashboard_page.py  首页（hero + 统计卡，非默认落地）
       ├─ ui/pages/custom_page.py     整理方案（已从导航移除，对象仍注册）
       ├─ ui/pages/history_page.py    整理历史 + 撤销
       ├─ ui/pages/settings_page.py   设置（深色/整理方式/子文件夹/检查更新/关于）
       ├─ ui/pages/tools_page.py      更多工具（UI-1.3 已从导航移除）
       └─ ui/state/worker.py          Worker(QThread) —— 所有阻塞任务离 UI 线程
            └─ core/scanner.py  scan()   → ScanResult
            └─ core/organizer.py plan()/summarize_plan()/move_items()/undo_plan()/execute_undo()
            └─ core/classifier.py classify()  (ext -> category key)
            └─ core/rules.py    DEFAULT_RULES / CATEGORY_NAMES / category_display
            └─ data/  database.py / history_repo.py / operation_repo.py / settings_repo.py
                 └─ SQLite: settings / history / operations 三表（database.py `_SCHEMA`）
```

要点（均来自实际代码）：
- 所有耗时业务（扫描、规划、移动、撤销）均经 `ui/state/worker.py` 的 `Worker(QThread)` 运行，`run()` 捕获异常并把 UI 可见错误交给 `utils/errors.py: friendly_message()`。
- 数据层为本地 SQLite，`DESKTOP_CLEANER_HOME` / `%APPDATA%/DesktopCleaner` / 项目根三态定位（`data/database.py:_app_base`）。
- `ui/features.py` 是功能注册表唯一事实来源；`LARGE_FILES`（大文件分析）**已注册，状态 `COMING_SOON`**（features.py:88-96），docstring 明确「功能真正上线时把 status 翻转为 AVAILABLE，UI 自动更新」。

---

## C. Scanner Audit

扫描入口与机制（`src/core/scanner.py`，实读全文）：

- 入口函数：`scan(root: Path, mode="type"|"date", recursive=False, rules=None, exclude_dirs=None) -> ScanResult`（scanner.py:69）。
- 遍历机制：`root.glob("*")`（非递归）或 `root.rglob("*")`（递归）（scanner.py:110），对每个条目 `entry.is_file()` 过滤目录（scanner.py:112）。
- 跳过规则（scanner.py:25,31,101,114-124）：
  - `_SYSTEM_FILES = {"desktop.ini", "thumbs.db", "ehthumbs.db"}`（:25）；
  - `_is_hidden()` 用 Windows ctypes `GetFileAttributesW(win_long(path)) & FILE_ATTRIBUTE_HIDDEN(0x2)`（:31-45）；
  - 跳过此前整理产物目录：`_ALWAYS_SKIP = set(CATEGORY_NAMES.values())` + 排除目录 + 日期目录（:101,122-123）。
- 安全保护：拒绝整理应用自身数据目录 `data_dir()`，命中抛 `ValueError`（:88-94）。
- 元数据读取（核心证据）：
  - `mode=="date"` 时调用 `_date_label(path)`（scanner.py:61）→ `path.stat().st_mtime` 格式化为 `%Y-%m`，stat 失败回退当前时间；
  - 每个候选文件 `f.stat().st_size`（scanner.py:135），`OSError` → size=0（:136-137）。
- 返回结构 `ScanResult`（scanner.py:48-58）：`root` / `files: List[Path]` / `by_category: Dict[str,int]` / `by_category_size: Dict[str,int]` / `total_size: int`；`total` 为 `len(files)` 属性。

结论：扫描引擎已经逐文件执行 `stat().st_size`，但 **size 只累加进聚合（`by_category_size` / `total_size`），`files` 列表仅存 `Path`，未保留任何 per-file size / mtime**。mtime 也仅在 date 模式用于分组，不保留。

---

## D. File Metadata

「file size 是否已存在于扫描结果 / domain model」——分两层回答：

| 层级 | 是否存在 | 字段 / 位置 | 生命周期 | 已用模块 |
|---|---|---|---|---|
| 聚合级（类别） | ✅ 存在 | `ScanResult.by_category_size: Dict[str,int]`（scanner.py:53） | 扫描循环内累加，随 ScanResult 返回 | organize_page._render_preview（organize_page.py:344）、preview_report 类别表（preview_report.py:87） |
| 聚合级（总计） | ✅ 存在 | `ScanResult.total_size: int`（scanner.py:54） | 同上 | organize_page._on_scan_done（organize_page.py:330）、preview_report summary（preview_report.py:59） |
| 单文件级 | ❌ 不存在 | `ScanResult.files: List[Path]` 仅存 Path | —— | plan() 遍历取 path（organizer.py:89-97） |
| 单文件 mtime | ❌ 不保留 | 仅 `_date_label()` 内部消费（scanner.py:61-66） | 即用即弃 | 仅 date 模式分组 |
| 单文件 size（规划期） | ⚠️ 临时存在 | `organizer.summarize_plan` 内 `it.source.stat().st_size`（organizer.py:123） | 仅用于类别聚合报告，不进 PlanItem | preview_report |

最小新增数据路径：为「大文件发现」引入 per-file size，可二选一（详见 L）：
1. 在 `ScanResult` 增加 `sizes: Dict[str, int]`（path_str -> bytes）或 `entries: List[FileMeta]`（path + size）；
2. 或独立新增一个 `scan_large_files()`，复用 `scan` 的过滤逻辑但返回 `(path, size)` 排序列表。

两者均无需重写遍历机制——stat 已经在做。

---

## E. Organizer Reuse

现有整理管道数据流（organize_page.py + organizer.py + operation_repo.py）：

```
scan() → ScanResult
   ↓
plan() → List[PlanItem{source, target, category}]     (organizer.py:74)
   ↓
summarize_plan() → dict{total, total_size, categories} (organizer.py:101)
   ↓  PreviewReportDialog（modal 安全门，preview_report.py）
   ↓
organize_page._task_organize:                         (organize_page.py:443)
   history_repo.create → plan → operation_repo.bulk_insert_pending
   → move_items(校验移动) → update_statuses_by_target → history_repo.update_status
   ↓
undo: execute_undo → apply_undo_result → update_status(undone) → 清空空目录
```

对照 §4 六个能力点的复用判断：

| 能力 | 现状 | 大文件功能复用度 |
|---|---|---|
| A. 扫描文件 | ✅ `scan()` 返回全部文件 Path | 直接复用（含隐藏/系统/输出目录过滤 + data_dir 保护） |
| B. 获取文件大小 | ✅ 聚合级有；单文件级需最小新增 | 复用 stat 结果，避免二次 stat |
| C. 按 size 排序 | ❌ 无任何排序 API | 新增：对 size 列表 `sorted(..., reverse=True)` 即可，O(n log n) |
| D. 展示给 UI | ✅ 现有按类别卡片 / 预览表 | 新增独立展示（见 F/G），不复用类别卡片 |
| E. 对选定文件安全移动 | ✅ `move_items` 逐文件校验、不覆盖不删除 | 若「大文件 → 可选整理」走既有 move 通道，直接复用 |
| F. 撤销/历史 | ✅ `undo_plan`/`execute_undo`/`history_repo` | 若大文件触达移动，天然落入既有 history/undo |

结论：**现有 scan + move_items + undo 链路足以承载「发现大文件 → 查看 → 可选整理」**，唯一必须新增的是单文件级 size 捕获与按大小排序/展示。不触碰 plan/organize/move/undo 任何逻辑。

---

## F. UI Options

以实际代码为依据评估（不臆测）：

### OPTION A — 整理方式增加「按大小」

- 改动面：`organize_page.py:109` `Segmented([("type","按类型"),("date","按日期")])`；`settings_page.py:89` 同款 Segmented；`custom_page.py:29-32` `_PLANS`；`scan()` 的 mode 分支（scanner.py:127-131）；`organizer._category_label`（organizer.py:68）；`preview_report` mode 文案（preview_report.py:51-53）。
- 语义冲突：`mode` 贯穿 scan/plan/organize/preview，「按大小」不是一种「整理/分类方式」（没有目标文件夹语义），强制塞入会导致「整理方式=按大小」却无法整理、或在 plan 阶段出现无意义移动方案。**与产品「整理，不删除」的整理语义混淆。**
- 破坏风险：中高（触碰 organize 主流程的 mode 分支，所有既有测试的 mode 契约需评估）。
- 用户理解成本：低到中（入口直观，但「按大小整理」含义歧义）。

### OPTION B — 独立「大文件分析」页 + Sidebar 入口（推荐）

- 改动面：新增一个 page（如 `src/ui/pages/large_files_page.py`）；`sidebar.py:36` `_NAV` 增加一项（注意 sidebar.py:33 注释「Navigation is closed to exactly four entries」为 UI-1.3 决策，需最小扩展为 5 项）；`app_shell.py:86-92` `_pages` 注册；`features.py` 将 `LARGE_FILES` 由 `COMING_SOON` 翻转 `AVAILABLE`（features.py:88-96，docstring 明确该契约）。
- 语义清晰：独立于「整理」，符合「发现 → 查看 → 理解 → 可选整理」的 MVP。
- 破坏风险：低（不触碰 organize 主流程、不动 scan/plan/move/undo）。
- 与未来重复文件：同属 storage 类（features.py 中 DUPLICATE_FINDER / LARGE_FILES / FOLDER_ANALYZER 同 category=storage），未来可在同一「空间分析」体系下扩展。

### OPTION C — 扫描结果内增加大小排序/筛选

- 改动面：`organize_page._render_preview`（organize_page.py:333-386）改动较大；类别卡片结构（cat-row/cat-bar）需加文件级明细或排序控件。
- 冲突：organize 预览的职责是「类别概览 + 整理确认」，混入大文件列表会让单一页面承载两种心智。
- 破坏风险：中（直接影响 1.1.1 已锁定预览结构）。

### OPTION D — 复用已移除的 CustomPage/ToolsPage

- `custom_page.py` 已从导航移除（sidebar.py:29-32 注释）；`tools_page.py` 已从导航移除（sidebar.py:33 注释），且 `get_features()` 默认排除 AVAILABLE（features.py:154-159）——即使翻转 LARGE_FILES 为 AVAILABLE，它也不会出现在 ToolsPage 列表里（该页只展示非 AVAILABLE）。
- 结论：**不可直接复用**，只能作为「新增独立页」时的导航落点参考。

### 方案对比

| 维度 | A | B（推荐） | C | D |
|---|---|---|---|---|
| UI 改动规模 | 中 | 中 | 中高 | 不可行 |
| 代码改动规模 | 中高（mode 扩散） | 中（新增页+导航） | 中（预览重构） | —— |
| 与产品定位一致 | 差（整理语义混淆） | 好（发现=分析） | 中 | —— |
| 用户理解成本 | 低-中 | 低 | 中 | —— |
| 与重复文件兼容 | 低 | 高 | 中 | —— |
| 对 1.1.1 破坏风险 | 中高 | 低 | 中高 | —— |

**推荐：OPTION B**（独立「大文件分析」页）。理由：职责分离、对既有 organize 主流程零破坏、与 features.py 注册表契约天然对接、为未来 storage 类工具（重复文件/文件夹分析）预留同一体系。

---

## G. Recommended UX

在推荐方案 B 下的最小视觉方案（保持现有视觉系统，不引入新设计语言）：

- **入口**：Sidebar 新增一行「大文件」或「空间」（介于「整理」与「整理历史」之间，或置于「整理历史」下方；沿用 `nav-item` 样式与 `pixmap()` 图标体系）。features.py `LARGE_FILES` 名称「大文件分析」，图标 📦（页面内可新增一个 `chart`/`gauge` 线框图标，icons.py 现无该图标）。
- **文案**：副标题对齐现有 `page-sub` 风格，如「扫描并查看当前目录占用空间较大的文件 — 只查看，不删除」。
- **配置区**：复用 organize_page 的 `step-card` 结构：`QLineEdit` 选目录 + 「选择文件夹」`secondary` 按钮 + 「开始扫描」`primary` 按钮（含「包含子文件夹」`ToggleSwitch`，默认关）。
- **状态**：复用 `Worker` + indeterminate `QProgressBar` + `page-sub` 状态行；扫描中禁止重复点击（沿用 `_set_busy` 模式）。
- **结果展示**：新页面内嵌一个表格/列表（沿用 `panel` + `tl-row` 或 `table` 样式），列：**文件名 / 大小 / 类型（category_display） / 所在子目录**；按 size 降序。顶部一行摘要「共 N 个文件 · 合计 X，最大：Y」。
- **排序**：默认 size desc；单文件大小用 `utils.format.human_size`（B/KB/MB/GB/TB，utils/format.py:5-14）。
- **用户操作**：MVP 阶段仅「查看」+ 打开所在文件夹（`os.startfile`/`QDesktopServices`，需实施阶段确认安全范围）；**可选**后续扩展「对选中大文件走既有安全整理/移动」。
- 不引入 dashboard、不引入空间占比环形图（属 FOLDER_ANALYZER/磁盘分析范畴，超 MVP）。

---

## H. Performance

基于实际扫描实现（scanner.py:110-139）的复杂度评估：

- 遍历：非递归 `glob("*")` 仅扫根目录一层；递归 `rglob("*")` 全子树。每个条目至少一次 `is_file()`（隐含 stat/lstat），候选文件再 `stat().st_size`（:135）。即 **每文件约 2 次 stat**，O(n)。
- 排序：`sorted(..., key=size, reverse=True)` O(n log n)。

| 文件量 | 预期行为 | 风险 |
|---|---|---|
| 1,000 | 毫秒~秒级 | 无 |
| 10,000 | 秒级 | 无；UI 在 Worker 线程，不冻结 |
| 100,000 | 数秒~数十秒（stat 与 glob 路径拼接为主） | 进度条为 indeterminate，无精确进度；内存 `List[Path]` 可承受 |
| 500,000 | 数十秒~分钟级；排序 O(n log n) | UI 不得一次渲染全部行 → **MVP 需限制展示 top-N（如 top 100）或分页**；内存需留意 |

结论（真实存在的风险，不过度优化）：
1. **展示层必须 top-N 截断或分页**——一次性向 QLayout/QTable 塞 10 万行会卡死 UI，这是 500K 量级唯一硬风险。
2. **scan 已逐文件 stat**，「大文件」复用 scan 不增加额外 stat 轮次；但若 date 模式（mtime）也纳入，每文件多一次 stat，非必要不引入。
3. 不引入目录递归容量分析（文件夹大小合计）——属磁盘空间分析器范畴，MVP 明确不做。

---

## I. Safety

现状（scanner.py + organizer.py 实测）：

- permission denied / stat failure：`f.stat().st_size` 包 `try/except OSError` → size=0（scanner.py:134-137），单文件失败不中断整体扫描。
- 隐藏 / 系统文件：`_is_hidden()`（:31）+ `_SYSTEM_FILES`（:25）跳过，防误扫。
- 应用自身数据目录：`data_dir()` 校验，抛 `ValueError`（:88-94）。
- 文件消失 / 被占用 / 移动失败：`move_items` 逐文件 `try/except`，记录 `failed_details`（organizer.py:171-190），不中断批次。
- 长路径：`win_long()`（utils/paths.py:13-28）已贯穿 `_is_hidden` / makedirs / move。

结论：**现有错误体系完全覆盖大文件扫描的异常面，直接复用，无需新错误系统**。唯一新增注意点：大文件页若在结果展示时对「文件已消失」的文件单独标记（stat 二次失败），属展示层优化而非错误体系重构（MVP 可不做）。

---

## J. Test Coverage

实测（pytest 收集 47 个测试，分布见下；另有 7 个独立运行脚本 `python tests/test_*.py`，非 pytest 收集）：

pytest 47 个测试来源：
- `tests/test_about_update.py`（15）：About 更新按钮状态机 / URL 白名单
- `tests/test_update.py`（8）：update version/manifest/checker/integrity/decision/manager
- `tests/test_reliability.py`（9）：WAL、并发、批量状态、**scan 去重/递归不重复/模式不串扰/符号链接**、失败明细、友好消息
- `tests/test_security.py`（4）：中断恢复、部分撤销、撤销不覆盖、**scanner 保护（data_dir）**
- `tests/test_p2_coverage.py`（4）：缺失源、WAL 升级、reconcile、日志格式
- `tests/test_windows_paths.py`（5）：长路径、真实长路径移动、safe helpers

独立脚本（非 pytest）：`test_core.py` / `test_appshell.py` / `test_dashboard.py` / `test_first_launch.py` / `test_phase5_e2e.py` / `test_preview.py` / `test_theme.py`。

与「大文件」直接相关的现有覆盖：
- scanner 基础行为：test_reliability（scan 去重/递归/模式/符号链接）、test_security（data_dir 保护）——**可复用，不冲突**。
- **缺失**：无 file-size fixture、无按 size 排序 fixture、无大文件扫描 fixture、无「top-N 截断」测试。实施阶段需新增（见 P/O）。

---

## K. Duplicate Compatibility

未来「重复文件查找」典型流程（size grouping → hash → duplicate groups → 用户选择 → safe move → undo）与本功能的兼容性评估：

- `features.py` 中 `DUPLICATE_FINDER` / `LARGE_FILES` / `FOLDER_ANALYZER` 同属 `category="storage"`，产品路线图天然相邻。
- 「大文件」若以 `(path, size)` 的条目列表为结果载体，与重复文件的第一阶段（size 分组）**共用同一 size 元数据**：未来重复文件功能可直接复用「单文件级 size 捕获 + 按大小分组」的基础，只需再加 hash 层。
- 但本阶段**明确禁止**：提前实现 hash、duplicate engine、复杂 domain abstraction。只做「真正需要的最小基础」——即捕获单文件 size 并按大小排序/展示。
- 设计提示（写入 O）：size 结果结构尽量简单（path + size），避免为「可能的未来」引入过度抽象。

---

## L. Proposed 1.2 Scope

**推荐 MUST HAVE（严格收窄）：**
「用户可以扫描并发现当前目录中的大文件，并按照文件大小查看结果（top-N）。」

- 用户入口：Sidebar「大文件分析」页（Option B）。
- 输入：目录路径 + 是否递归（ToggleSwitch，默认关，与现有 recursive 语义一致）。
- 扫描范围：复用 `scan()` 的过滤规则（隐藏/系统/输出目录/data_dir 保护）。
- 输出：`(path, size)` 列表，按 size 降序，展示文件名 / 大小 / 类型 / 所在子目录；顶部摘要（文件数 + 合计大小）。
- 排序规则：size desc；同大小按路径字符串升序（确定性）。
- UI 行为：Worker 线程扫描、indeterminate 进度、扫描中禁用重复点击、结果 top-N（建议 100）展示。
- 错误处理：复用 `friendly_message`（utils/errors.py）；stat 失败 size=0 不中断。
- 性能边界：top-N 截断；不做目录递归容量合计。
- 测试要求：新增 size 捕获测试、排序测试、top-N 测试、扫描隔离（DESKTOP_CLEANER_HOME + offscreen）测试；既有 47 测试必须保持 PASS。
- 明确禁止（本阶段及实施首版）：删除文件、一键清理、注册表/浏览器缓存/系统优化、自动删除、AI 判断垃圾、目录容量分析（磁盘空间分析器）、hash/重复文件引擎、任何移动动作（除非后续单独授权「大文件→安全整理」）。

**SHOULD HAVE（可选，二次迭代）：** 打开所在文件夹；对选中大文件走既有安全移动通道。

**NOT IN SCOPE（1.2 明确排除）：** 删除/清理类功能、空间占比环形图、磁盘分析器、重复文件、文件夹容量合计、定时/开机扫描。

---

## M. Out of Scope

明确不属于 1.2（依据 §L 与产品哲学「整理，不删除」）：

- ❌ 删除垃圾文件 / 一键深度清理 / 注册表清理 / 浏览器缓存清理 / 系统优化 / 内存优化
- ❌ 自动删除、AI 判断垃圾文件
- ❌ FULL DISK SPACE ANALYZER（目录递归容量分析、可视化空间占比）
- ❌ 重复文件查找（hash / duplicate engine）
- ❌ 修改现有 organize 主流程、scan/plan/move/undo 逻辑
- ❌ 修改 1.1.1 已锁定内容（About 作者/微信/版权/指纹、更新源、build.spec）

---

## N. Implementation Impact

以下为**现有真实文件**（非虚构），未来实施阶段预计涉及的清单：

| FILE | ROLE | EXPECTED CHANGE | RISK |
|---|---|---|---|
| `src/core/scanner.py` | 扫描引擎 | 增加 per-file size 捕获（`ScanResult.sizes` 或独立扫描函数） | LOW（stat 已在做，仅保留结果） |
| `src/core/rules.py` | 分类规则 | 无改动（复用 `category_display`） | —— |
| `src/ui/pages/large_files_page.py`（新增） | 大文件分析页 | 新增页面：目录选择 + 扫描 + top-N 表格 | LOW（新页面，不动既有页面） |
| `src/ui/widgets/sidebar.py` | 导航 | `_NAV` 增加一项（sidebar.py:36） | LOW（UI-1.3 决策注释需同步更新） |
| `src/ui/app_shell.py` | 路由 | `_pages` 注册新页（app_shell.py:86-92） | LOW |
| `src/ui/features.py` | 功能注册表 | `LARGE_FILES` status: COMING_SOON → AVAILABLE（features.py:94） | LOW |
| `src/ui/icons.py` | 图标 | 新增 `chart`/`gauge` 线框图标（如需要） | LOW |
| `src/utils/format.py` | 格式化 | 无改动（`human_size` 已存在，utils/format.py:5） | —— |
| `tests/test_large_files.py`（新增） | 测试 | size 捕获 / 排序 / top-N / 隔离 | LOW |

预计不动：`organizer.py` / `classifier.py` / `database.py` / `operation_repo.py` / `history_repo.py` / `settings_repo.py` / `update/*` / `about.py` / `constants.py` / `update_dialog.py` / `build.spec` / `main.py`。

---

## O. Scope Lock

**PHASE 1.2 LARGE FILE DISCOVERY — STATUS: READY FOR IMPLEMENTATION**

精确 Scope Lock（实施阶段必须遵守）：

1. **功能名称**：大文件分析（features.py key=`LARGE_FILES`，名称「大文件分析」，图标 📦）。
2. **用户入口**：Sidebar 新增「大文件分析」页（Option B）。
3. **输入**：目录路径（QLineEdit + QFileDialog）+ 递归开关（ToggleSwitch）。
4. **扫描范围**：复用 `scan()` 过滤（隐藏/系统文件/已整理输出目录/应用数据目录保护）。
5. **输出**：`(path, size)` 列表按 size 降序；展示文件名 / 大小 / 类型 / 所在子目录；顶部摘要。
6. **排序规则**：size desc；同大小按路径字符串升序。
7. **UI 行为**：Worker 线程、indeterminate 进度、扫描中禁重、top-N=100、结果页保持现有视觉（panel/tl-row 风格）。
8. **错误处理**：复用 `friendly_message`；stat 失败 size=0 不中断。
9. **性能边界**：top-N 截断；不做目录递归容量。
10. **测试要求**：新增大文件测试（隔离 `DESKTOP_CLEANER_HOME` + `QT_QPA_PLATFORM=offscreen`）；既有 47 测试保持 PASS。
11. **明确禁止**：删除/清理/注册表/缓存/系统优化/自动删除/AI 判断/目录容量分析/重复文件 hash/移动动作（除非后续单独授权）。

---

## P. Implementation Plan

未来实施阶段最小步骤（本阶段不执行）：

- STEP 1：`src/core/scanner.py` 增加 per-file size 捕获（最小结构，如 `ScanResult.sizes` 或独立函数）。
- STEP 2：`src/ui/pages/large_files_page.py` 新增页面（目录选择 + Worker 扫描 + top-N 表格）。
- STEP 3：`src/ui/widgets/sidebar.py` + `src/ui/app_shell.py` 注册入口与路由。
- STEP 4：`src/ui/features.py` 翻转 `LARGE_FILES` → AVAILABLE（可选，配合页面落地）。
- STEP 5：新增 `tests/test_large_files.py`（size 捕获 / 排序 / top-N / 隔离）。
- STEP 6：回归 —— 全量 pytest（47 + 新增）PASS；release_validate 不受影响。
- STEP 7：手动 GUI 验证（offscreen 渲染 + 实机窗口可见性）。

---

## Q. Risks

| 风险 | 等级 | 说明与缓解 |
|---|---|---|
| 大结果集渲染卡死 | 中 | top-N=100 截断（§H 唯一硬风险），禁止一次渲染全量 |
| Sidebar 导航从 4 项变 5 项 | 低 | UI-1.3 注释「closed to four entries」需同步更新；`test_appshell` 有页面注册断言，改后回归 |
| features.py 翻转 AVAILABLE 后 ToolsPage 行为变化 | 低 | `get_features()` 默认排除 AVAILABLE（features.py:154-159），翻转后大文件不再出现在 ToolsPage（该页已不可达），无副作用；需在实施时回归确认 |
| per-file size 引入 scope creep（目录容量） | 低 | Scope Lock 明确「FILE SIZE DISCOVERY ≠ DISK SPACE ANALYZER」，禁止递归容量 |
| 与 1.1.1 锁定内容漂移 | 低 | 只增不改；organize 主流程、About、更新系统、build.spec 均不触碰 |

---

## R. Final Recommendation

基于全部实际证据（代码为唯一事实来源，未使用「应该/大概/推测」表述）：

- **Baseline**：`main` @ `9532e38`，工作树对本范围 CLEAN（仅 2 个已知外部 R5 未跟踪文档）。
- **架构结论**：现有 scan（过滤+stat）→ Worker 线程 → 既有安全移动/撤销链路，足以承载「发现大文件 → 查看 → 可选整理」；唯一缺口是单文件级 size 未保留。
- **Size 元数据结论**：聚合级（`by_category_size` / `total_size`）已存在；单文件级不存在，最小新增路径是保留 stat 结果。
- **推荐 UI**：OPTION B —— 独立「大文件分析」页 + Sidebar 入口（职责分离、零破坏、与 features 注册表契约一致）。
- **推荐实施范围**：见 §L MUST HAVE（扫描+查看+top-N），严格排除清理/删除/磁盘分析/重复文件。
- **预计影响文件**：scanner.py（+size）、新增 large_files_page.py、sidebar.py、app_shell.py、features.py、（可选）icons.py、新增测试文件；其余模块零改动。
- **测试影响**：既有 47 测试保持 PASS；新增大文件测试；独立脚本（7 个）不受影响。
- **风险**：仅「大结果集渲染」为中风险（top-N 缓解）；导航 4→5 项与 features 翻转为低风险（回归确认即可）。

**PHASE 1.2 — DISCOVERY AUDIT COMPLETE — STATUS: READY FOR IMPLEMENTATION**

等待下一阶段明确授权：`PHASE 1.2 — CONTROLLED IMPLEMENTATION`
