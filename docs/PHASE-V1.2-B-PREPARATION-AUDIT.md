# PHASE V1.2-B-PREPARATION — Product Gap & Architecture Audit

| 项 | 值 |
|---|---|
| 阶段 | PHASE V1.2-B-PREPARATION |
| 性质 | **只读审计与规划**（不写代码、不改源码/测试/配置、不提交 Git） |
| 日期 | 2026-09-29 |
| 正式基线 HEAD | `4d0d2a5a2eaa8192ae8d26ad59c9c548e740d7ed` |
| 基线 commit | `feat: establish v1.2-a feature baseline` |
| 父提交 | `20f949402ba5ed042b05d931b629c087b26b28bd` |
| 最终状态 | **V1.2-B-PREPARATION COMPLETE / IMPLEMENTATION NOT AUTHORIZED / HARD STOP** |

> 本阶段目标不是写代码。目标是先把 V1.2-B 的边界定义清楚，
> 避免在 V1.2-A 刚刚封存后再次出现功能堆叠。

---

## 1. V1.2-A baseline verification

### 1.1 Git 状态（只读复核，未发生任何漂移）

```
HEAD        = 4d0d2a5a2eaa8192ae8d26ad59c9c548e740d7ed
HEAD^{tree} = 34f28abbb6104fe5ed4344957149c08dae9f5e90
HEAD^       = 20f949402ba5ed042b05d931b629c087b26b28bd
staged      = 0 files
commit stat = 25 files changed, 4975 insertions(+), 9 deletions(-)
```

### 1.2 工作区（`git status --short`）

```
 M src/core/scanner.py
 M src/ui/app_shell.py
 M src/ui/features.py
 M src/ui/widgets/sidebar.py
?? .workbuddy-ai/
?? docs/PHASE-1.2-LARGE-FILE-DISCOVERY-AUDIT.md
?? docs/PHASE-V1.2-A-CLOSURE-REPORT.md
?? docs/PHASE_R5.1_RELEASE_ARTIFACT_SYNC.md
?? docs/PHASE_R5_FINAL_RELEASE_AUDIT.md
?? src/ui/pages/large_files_page.py
?? tests/test_large_files.py
```

与 V1.2-A-CLOSURE 结束时的状态**逐行一致**：4 个 PHASE 1.2 已修改文件 + 4 个 PHASE 1.2 未跟踪产物 + `.workbuddy-ai/` + 上阶段产出的收尾报告。**未新增、未删除任何条目。**

### 1.3 V1.2-A test baseline（两棵树分别实测）

| 树 | 取得方式 | 结果 |
|---|---|---|
| **提交树（V1.2-A）** | `git archive HEAD \| tar -x -C D:/Temp/dc_v12b_probe` | **96 passed** |
| **工作区（含 PHASE 1.2）** | 原地 `pytest -q` | **107 passed** |

差值 **11** = `tests/test_large_files.py`（PHASE 1.2，故意不在提交树内），已核实。

**结论：V1.2-A commit 未发生任何漂移。基线可信、可回溯、可独立验证。**

---

## 2. 当前产品能力地图

### 2.1 运行期实测事实（offscreen 构建 AppShell，非静态推断）

```
_pages (9)   = analysis, custom, empty, history, home, large, organize, rules, settings
Sidebar nav  = organize, large, analysis, empty, history, settings, rules  (+ about)
默认落地     = OrganizePage ("organize")
```

导航顺序（`sidebar._NAV`）：`organize → large → analysis → empty → history → settings → rules`，
底部 `about`（模态对话框，非页面）。

### 2.2 分类清单

#### A. 已完成并稳定（运行期可达 / 有测试）

| 能力 | 模块 | 入口 |
|---|---|---|
| 扫描 + 预览 | `core/scanner.py`、`core/organizer.plan/summarize_plan` | 整理页 |
| 按类型 / 按日期整理（移动 + 逐文件校验 + 冲突改名） | `core/organizer.move_items` | 整理页 |
| 整理前模拟报告安全门 | `ui/preview_report.py` | 整理页 |
| 两阶段落库 + 启动对账 | `data/operation_repo.{bulk_insert_pending,update_statuses_by_target,reconcile_pending}` | `main.py` |
| 整理历史 + 单次撤销 | `ui/pages/history_page.py`、`ui/undo.run_undo` | 整理历史页 |
| 设置（主题 / 模式 / 递归 / 检查更新 / 关于） | `ui/pages/settings_page.py` | 设置页 |
| 主题系统（浅 / 深） | `ui/theme/*`（+ `ui/theme_manager.py` 兼容 shim） | 顶栏 |
| 检查更新（Option B，fail-closed） | `update/*` | 设置页 / 关于 |
| 关于 / 首次启动引导 | `ui/about.py`、`ui/welcome.py` | 顶栏 / 启动 |
| **F1 空文件夹清理** | `core/empty_folders.py` + `ui/pages/empty_folders_page.py` | 侧栏「空文件夹」 |
| **F2 文件夹分析** | `core/analysis.py` + `ui/pages/analysis_page.py` | 侧栏「文件夹分析」 |
| **F3 导出报告** | `core/report.py` + `analysis_page._export` | 文件夹分析页内按钮 |
| **F4 自定义规则** | `core/custom_rules.py` + `ui/pages/rules_page.py` | 侧栏「自定义规则」 |
| 长路径安全 | `utils/paths.win_long` | 横切 |
| 友好错误映射 | `utils/errors.py` | `Worker` |
| 后台任务执行器 | `ui/state/worker.Worker` | 5 个页面 |

#### B. 已实现但尚未完整接入

| # | 事实 | 证据 |
|---|---|---|
| B1 | **功能注册中心与已上线功能脱节** | `ui/features.py` 中 `EMPTY_FOLDER` 仍为 `COMING_SOON`、`FOLDER_ANALYZER` 仍为 `PLANNED`，而两者已作为独立导航页上线；`README.md §8.1` 同样仍写「即将上线 / 规划中」 |
| B2 | **注册中心在运行期没有任何消费者** | `ui/features.py` 仅被 `ui/pages/tools_page.py` 与 `ui/coming_soon.py` 引用，而这两者均不可达（见 E）。即"唯一事实来源"当前**不被产品 UI 读取** |
| B3 | **注册中心在两条线上同时漂移** | 工作区（PHASE 1.2）已把 `LARGE_FILES` 翻为 `AVAILABLE`；V1.2-A 提交树里仍是 `COMING_SOON` |
| B4 | **导出报告没有历史记录** | F2/F3 为只读，不写 `history`/`operations`；导出路径只存在于当次弹窗，重启后不可追溯 |
| B5 | **F1 未复用统一安全门** | 空文件夹清理用自己页面的二次确认，而非 `ui/preview_report.PreviewReportDialog`；两者语义相同、实现不同 |
| B6 | **`compute_clean_score` / `ScoreRing` 已实现但页面不可达** | 接线在 `ui/pages/dashboard_page.py`，而 `home` 无侧栏入口 |

#### C. 已有基础设施但缺少产品闭环

| # | 基础设施 | 现状 | 缺失的闭环 |
|---|---|---|---|
| C1 | `update/integrity.sha256_bytes` / `verify_sha256` | 已实现且有测试，仅服务 Option B | **无任何"内容比对 / 去重"消费者** |
| C2 | `ScanResult.sizes`（PHASE 1.2 新增） | 单次 stat 记录每文件字节数 | 仅被 `large_files_page` 使用；是"按 size 分桶"的天然输入 |
| C3 | `data/settings_repo`（通用 KV） | `custom_rules` 已用它存 JSON | 任何"用户偏好 / 持久清单"都可复用，**无需 schema 变更** |
| C4 | `operations` 表 + `pending` 两阶段 + 启动对账 | 一套完整"可撤销文件操作"范式 | **只有 `move` 一种 operation**，无 rename 语义 |
| C5 | `core/report.py` 的 `REPORT_SCHEMA` + `rules_fingerprint` | 报告溯源机制已建立 | **输入被硬绑定为 `AnalysisResult`**，无第二个生产者 |
| C6 | `utils/logger` 文件日志 | 已就绪 | **无"导出诊断包"的产品入口** |
| C7 | `ui/state/worker.Worker` | 通用后台执行器 | 无（复用良好） |

#### D. COMING_SOON / PLACEHOLDER

`ui/features.py` 内：`EYE_CARE`、`QUICK_LOCK`、`DUPLICATE_FINDER`、`EMPTY_FOLDER`\*、`BATCH_RENAME`、`QUICK_SEARCH`、`FOLDER_ANALYZER`\*、`SCHEDULED_CLEAN`、`STARTUP_CLEAN`。

\* 状态过期：`EMPTY_FOLDER` / `FOLDER_ANALYZER` 已实际上线（属 B1）。

#### E. 死代码 / 历史遗留（运行期不可达）

已由 `docs/LEGACY_SURFACE_INVENTORY.md` 登记，处置原则为**保留、不删除**：

| 模块 | 行数 | 不可达原因 |
|---|---|---|
| `src/ui/pages/tools_page.py` | 124 | 导航已移除（UI-1.3 Decision 02），`_pages` 无 `tools` 键 |
| `src/ui/coming_soon.py` | 74 | 仅被 `tools_page` 引用 |
| `src/ui/features.py` | 166 | 仅被 `tools_page` / `coming_soon` 引用 |
| `src/ui/pages/dashboard_page.py` | 240 | 侧栏无 `home` 入口 |
| `src/ui/pages/custom_page.py` | 192 | 侧栏无 `custom` 入口（仍在 `_pages` 实例化） |
| **合计** | **796** | |

**本轮新增发现（未在原清单登记）：**

- `src/ui/styles.py`（11 行）：导出的 `STYLESHEET` **无任何消费者**（`ui/theme_manager` 直接走 `build_stylesheet`）。
- **原清单的实测快照已过期**：它记录 `_pages` 有 6 个键、侧栏 4 个入口；当前是 **9 个键 / 7 个入口**（V1.2-A 新增 analysis / empty / rules）。
- ⚠️ `src/ui/theme_manager.py`（8 行）与 `src/ui/themes.py`（18 行）是**活跃的兼容 shim**（被 `app_shell` / `icons` / 几乎所有页面 import），**不是死代码**——不要与上述清单混同误删。

#### F. PHASE 1.2 当前工作（冻结，本阶段不触碰）

| 文件 | 状态 | 内容 |
|---|---|---|
| `src/core/scanner.py` | M | `ScanResult.sizes`（单次 stat 保留字节数） |
| `src/ui/features.py` | M | `LARGE_FILES` → `AVAILABLE` |
| `src/ui/app_shell.py` | M（混合） | `large` 页面接线 |
| `src/ui/widgets/sidebar.py` | M（混合） | `("large", "search", "大文件")` 导航行 |
| `src/ui/pages/large_files_page.py` | ?? | 341 行 |
| `tests/test_large_files.py` | ?? | 11 个测试 |
| `docs/PHASE-1.2-LARGE-FILE-DISCOVERY-AUDIT.md` | ?? | 审计文档 |

运行期事实：`large` 已是**第 2 个导航项**，`LargeFilesPage` 已注册并可路由。**未提交、不在 V1.2-A commit 内。**

#### G. 真正适合 V1.2-B 的候选能力

- 重复文件查找（`DUPLICATE_FINDER`）
- 批量重命名（`BATCH_RENAME`）
- 报告导出能力收口（把 F3 从"分析"扩展到"整理 / 清理"）
- 自动化类：托盘常驻 / 定时整理 / 开机整理
- 系统级 / 战略级：资源管理器右键菜单、自动更新 Option A、代码签名

---

## 3. Product gaps

### 3.1 V1.2-A 已经解决了什么

V1.2-A 把「整理」从**单一动作**扩展为**存储管理工作台**，并且**没有新增第二条文件操作路径**：

- `core/empty_folders.cleanup()` 显式委托 `core.organizer.move_items()`（唯一执行器）；
- `core/analysis.py` 完全没有写路径；
- `core/custom_rules` 只做规则解析/校验，从不改 `DEFAULT_RULES`；
- `core/report.py` 只读结果对象、只写用户指定文件。

它补上了四个真实断点：

| 用户断点 | V1.2-A 的回答 |
|---|---|
| 「文件清完了，空文件夹还留着」 | F1 空文件夹清理（移入同根隔离区，可撤销） |
| 「我不知道空间去哪了」 | F2 文件夹分析（只读结构快照） |
| 「我想留一份记录 / 发给别人」 | F3 导出报告（JSON / CSV，带溯源） |
| 「我的 .psd 被当成图片 / 我想关掉某个分类」 | F4 自定义规则（用户规则 > 内置，内置表运行期不可变） |

### 3.2 当前工作流仍然存在的明显断点（仅基于代码与已验证事实）

| # | 断点 | 代码事实 |
|---|---|---|
| G1 | **「清理」只覆盖零字节文件夹，不覆盖"重复内容"** | 全仓库**没有任何重复检测代码**；唯一相关的 `sha256_bytes` 位于 `update/integrity.py`，且无内容比对消费者（C1） |
| G2 | **「整理」只能归类，不能改名** | 组织后文件名保持原样；`operations` 表只有 `move` 语义，无 rename（C4） |
| G3 | **导出能力被锁死在"分析"上** | `core/report.build_report(result: AnalysisResult)` 硬绑定类型；整理历史 / 空文件夹清理**没有报告出口**（C5） |
| G4 | **分析 / 导出产物不可追溯** | `history` 表只有 `type` / `date` / `empty_folders` 三种 mode，没有分析或导出的记录（B4） |
| G5 | **注册中心与产品事实不一致（对用户可见）** | `features.py` 与 `README §8.1` 仍称「空文件夹清理：即将上线 / 文件夹分析：规划中」，而它们在侧栏已可用（B1） |

### 3.3 哪些现有能力可以自然形成下一个完整闭环

- **重复文件查找** —— 能同时用上 C2（size 分桶）+ C1（SHA-256 确认）+ `move_items`（隔离区 / 可撤销）+ C4（两阶段落库）+ `Worker`（后台）。**闭环最完整**，但需要新增核心服务 + 新页面 + 新的动作语义。
- **报告导出收口** —— 能用上 C5 的 schema / fingerprint 机制；但需要把 `build_report` 的输入从具体类型抽象为"报告源"。**改动面最小**。
- **批量重命名** —— 能用上 `plan → 预览 → 执行 → 撤销` 范式与 `win_long`；但**需要为 `operations` 引入 rename 语义**（数据层改动最大）。

### 3.4 哪些功能虽然存在但此刻加入会造成范围膨胀

- **托盘常驻 / 定时整理 / 开机整理 / 右键菜单**：都要引入**应用生命周期之外**的系统集成面（注册表、任务计划、常驻进程）。`main.py` 目前**无 CLI 参数入口**，需先建 CLI 层。与"一次打开、一次整理"的现有形态冲突。
- **自动更新 Option A + 代码签名**：属发布链工程而非产品能力；牵动 `build.bat` / `build.spec` / `update/*` 与证书流程。
- **i18n / 深色跟随系统**：低风险，但与"把整理做深"无关，工作量与收益不成比例。

### 3.5 哪些功能应该明确后置

- 所有需要**系统级注册**的（托盘 / 定时 / 开机 / 右键菜单）
- 所有需要**代码签名或自替换**的（自动更新 Option A）
- 所有**跨网络 / 云端**的（AI 分类）——与"完全本地、数据不上传"的产品承诺冲突
- 死代码处置与测试去重——应**独立阶段**处理，不得顺手做

---

## 4. V1.2-B candidates（最多 3 个）

> 以下仅为事实性分析。**不含 best/worst、不含 ranking、不含 score、不做自动选型。**

### 候选 1 — 重复文件查找（`DUPLICATE_FINDER`）

| 维度 | 事实 |
|---|---|
| **功能目标** | 找出内容相同的文件组，每组保留一份，其余移入隔离区（可撤销） |
| **用户工作流** | 选目录 → 后台扫描（分桶 → 采样 → 全量哈希）→ 分组预览 → 勾选保留项 → 二次确认 → 移入隔离区 → 可一键撤销 |
| **现有基础** | `ScanResult.sizes`（分桶输入）；`update/integrity.sha256_bytes`（确认原语）；`organizer.move_items`（唯一执行器）；`operations` 两阶段 + 对账；`Worker`；`empty_folders.QUARANTINE_DIRNAME` 隔离区先例 |
| **缺口** | 无任何重复检测模块；无"组"这一数据结构；无"每组至少保留一份"的强制约束；无大目录哈希的进度模型 |
| **修改范围** | 新增 `core/duplicates.py`、`ui/pages/duplicates_page.py`；改 `core/__init__.py`、`ui/app_shell.py`、`ui/widgets/sidebar.py`、`ui/icons.py`、`build.spec` |
| **测试范围** | 新 `tests/test_duplicates.py`：分桶正确性、采样排除、全量确认、**每组至少保留一份**、不跟随 reparse point、长路径、TOCTOU（扫描后被改）、空目录 / 单文件 / 全同 / 全异边界 |
| **风险** | **中**。唯一动作是"移入隔离区"，复用既有引擎；但必须硬性保证"每组至少保留一份"，且哈希失败/文件消失必须降级为"跳过"而非"视为唯一" |
| **与 V1.2-A 的关联** | 复用 F1 的隔离区概念与同一执行器；`by_extension`/`by_category` 分布可为分组提供 UI 维度 |
| **能否独立闭环** | **能**（扫描 → 预览 → 执行 → 撤销 → 历史，全链路可闭合） |

### 候选 2 — 批量重命名（`BATCH_RENAME`）

| 维度 | 事实 |
|---|---|
| **功能目标** | 按模板批量重命名文件（序号 / 日期 / 查找替换 / 大小写），可预览、可撤销 |
| **用户工作流** | 选目录 → 设模板 → **实时新旧对照预览** → 冲突/非法字符拦截 → 执行 → 撤销还原原名 |
| **现有基础** | `plan → 预览 → 执行 → 撤销` 范式；`win_long`；`Worker`；`settings_repo` 可存模板 |
| **缺口** | `operations` 表**只有 move 语义**；`run_undo` 只做反向移动；无模板引擎；无改名冲突/保留名（CON/PRN/NUL）校验 |
| **修改范围** | 新增 `core/rename.py`、`ui/pages/rename_page.py`；**改 `data/operation_repo.py`（新增 operation type 或新表）**；改 `ui/undo.py`（支持 rename 逆向）；改 `core/__init__.py`、`app_shell.py`、`sidebar.py`、`icons.py`、`build.spec` |
| **测试范围** | 新 `tests/test_rename.py`：模板正确性、非法字符、保留名、超长路径、名称冲突、部分失败、撤销还原原名、`operations` 向后兼容 |
| **风险** | **中-高**。改名是"原地修改"，比移动更难撤销；`_SCHEMA` 使用 `CREATE TABLE IF NOT EXISTS`，**新增列需要显式迁移逻辑**——这是本阶段最大的数据层改动 |
| **与 V1.2-A 的关联** | 复用同一撤销范式与 `history`/`operations` 表；`history.mode` 需新增 `rename` |
| **能否独立闭环** | **能**，但前提是数据层迁移先落地 |

### 候选 3 — 报告导出能力收口（把 F3 扩展到整理 / 清理）

| 维度 | 事实 |
|---|---|
| **功能目标** | 让「整理历史」与「空文件夹清理」也能导出报告，与 F3 共用同一 schema / 溯源机制 |
| **用户工作流** | 整理历史页 → 选一条记录 → 「导出报告」→ 选 JSON/CSV → 落盘 → 可"打开所在文件夹" |
| **现有基础** | `core/report.py` 的 `REPORT_SCHEMA` / `CSV_COLUMNS` / `CSV_SECTIONS` / `write_csv` / `write_json` / `export` 全部可复用；`history` + `operations` 已含全部数据；`analysis_page._export` 已有完整交互先例 |
| **缺口** | `build_report(result: AnalysisResult)` 输入被硬绑定；无"从 history/operations 构造报告 dict"的纯函数；`history_page` 无导出入口 |
| **修改范围** | 泛化 `core/report.py`（或新增 `core/history_report.py`）；改 `ui/pages/history_page.py`（加按钮）；**不改 `app_shell.py` / `sidebar.py` / `build.spec`** |
| **测试范围** | 新 `tests/test_history_report.py`（schema 稳定性、CSV 形状、空历史边界、溯源字段）；**F3 现有 7 个测试必须零回归** |
| **风险** | **极低**。纯只读 + 只写用户指定文件；无文件系统副作用 |
| **与 V1.2-A 的关联** | **直接延续 F3**（同一模块、同一 schema）；同时缓解 G3 / G4 |
| **能否独立闭环** | **能**，且不需要新增导航项 |

---

## 5. 建议的 V1.2-B scope

### 5.1 建议

> **V1.2-B = 报告导出能力收口**：把 F3 的导出从"仅分析"扩展为
> **「分析 / 整理 / 清理」三类记录均可导出**，共用同一 `REPORT_SCHEMA` 与溯源机制。

**Definition of Done（建议）**

1. `core/report.py` 的输入从具体类型 `AnalysisResult` 抽象为"报告源"，**F3 现有 7 个测试零回归**；
2. 新增从 `history` + `operations` 构造报告 dict 的**纯函数**（无 Qt、无写盘副作用）；
3. `ui/pages/history_page.py` 增加「导出报告」入口，复用 `export()` 与 F3 的交互模式（含"打开所在文件夹"）；
4. 报告含 `mode`（type / date / empty_folders）与 `rules_version` 溯源字段；
5. 新增测试覆盖 schema 稳定性、CSV 形状、空历史边界；
6. **不新增导航项、不改 `app_shell.py` / `sidebar.py` / `build.spec`。**

### 5.2 为什么它与 V1.2-A 最自然衔接

1. **同一个模块、同一份 schema。** 它不是新能力，而是 V1.2-A 留下的**未完成边**：F3 定义了 `REPORT_SCHEMA` 与 `rules_fingerprint` 机制，却只有一个生产者。收口 = 把已有机制用满。
2. **复用率最高、新增面积最小。** 不引入新核心服务族、不引入新数据结构、不改数据层、不新增页面。
3. **零 schema 变更、零写路径。** 纯读取 `history`/`operations`，只写用户显式指定的一个文件，与 V1.2-A 的安全模型完全同构。
4. **不触碰导航注册面。** 这是本阶段**决定性的架构理由**——见 §9：`app_shell.py` 与 `sidebar.py` 目前**同时携带未提交的 PHASE 1.2 改动**，任何"新增导航项"的 V1.2-B 功能都会再次触发混合文件分离问题。本 scope 完全不碰这两个文件。
5. **直接缓解已识别的断点 G3 / G4**，且不产生新的产品承诺。

### 5.3 为什么其它能力应后置

| 能力 | 后置理由 |
|---|---|
| **重复文件查找** | 用户价值最高，但它是一个**新的能力族**：新核心服务 + 新页面 + 新导航项 + 新动作语义（"每组至少保留一份"）。新增导航项 ⇒ **必须改 `app_shell.py` / `sidebar.py`** ⇒ 与未提交的 PHASE 1.2 改动正面冲突。应作为 **V1.2-C** 单独立项，且**必须在 PHASE 1.2 收尾提交之后**。 |
| **批量重命名** | 需要为 `operations` 引入 rename 语义（新增列/表 + 迁移），是**数据层改动**；且"原地改名"的撤销风险高于移动。改动面与风险都不适合紧跟 V1.2-A 封存之后。 |
| **托盘 / 定时 / 开机 / 右键菜单** | 需要应用生命周期之外的系统集成面与 CLI 入口，属**形态变更**而非功能增量。 |
| **自动更新 Option A / 代码签名** | 发布链工程，需证书与签名流程；属**独立阶段**。 |
| **注册中心与 README 同步（G5）** | **技术上被阻塞**：`ui/features.py` 当前是 PHASE 1.2 已修改文件。任何对它的编辑都会混入 PHASE 1.2。**必须在 PHASE 1.2 收尾提交之后**单独处理。 |
| **死代码处置（796 行）** | `LEGACY_SURFACE_INVENTORY.md` 已明确「保留，不删除」，且需同步 `build.spec` / README。属**独立阶段**。 |
| **测试去重** | 与产品能力无关，属工程卫生，独立处理。 |

---

## 6. Explicitly deferred items

| # | 项目 | 后置原因 | 前置条件 |
|---|---|---|---|
| D1 | 重复文件查找（`DUPLICATE_FINDER`） | 新能力族 + 新导航项，与 PHASE 1.2 未提交改动冲突 | PHASE 1.2 收尾提交 |
| D2 | 批量重命名（`BATCH_RENAME`） | 需数据层迁移（operation type） | 独立设计阶段 |
| D3 | 托盘常驻 / 定时整理 / 开机整理 | 需应用生命周期之外的系统集成 + CLI 入口 | 独立设计阶段 |
| D4 | 资源管理器右键菜单 | 注册表写入，需可干净卸载 | 独立阶段 |
| D5 | 自动更新 Option A（下载 + 校验 + 替换） | 发布链工程，需 Authenticode | 代码签名先行 |
| D6 | 代码签名 + SmartScreen 声誉 | 证书成本与流程 | 独立阶段 |
| D7 | 注册中心 / README 同步（G5） | `ui/features.py` 是 PHASE 1.2 已修改文件 | PHASE 1.2 收尾提交 |
| D8 | 死代码处置（796 行 + `ui/styles.py`） | 清单已明示「保留，不删除」；需同步 `build.spec` / README | 独立阶段 + Owner 授权 |
| D9 | 测试去重（`test_navigation.py` 与 `test_large_files.py` 概念重叠） | 工程卫生，非产品能力 | 独立阶段 |
| D10 | i18n / 深色跟随系统 | 与"把整理做深"无关，收益不成比例 | 未排期 |
| D11 | AI / 云端分类 | 与"完全本地、数据不上传"承诺冲突 | 未排期（且需重新论证） |
| D12 | `.workbuddy-ai/` 的 `.gitignore` 条目 | 属配置修改，本阶段禁止 | PHASE 1.2 收尾阶段一并处理 |

---

## 7. Architecture impact

对三个候选的逐项影响（与 §4 一致，此处为对照表）：

| 影响维度 | 候选 1 重复文件查找 | 候选 2 批量重命名 | 候选 3 报告导出收口 |
|---|---|---|---|
| 涉及模块 | `core/duplicates.py`(新)、`ui/pages/duplicates_page.py`(新)、`core/__init__.py`、`app_shell.py`、`sidebar.py`、`icons.py`、`build.spec` | `core/rename.py`(新)、`ui/pages/rename_page.py`(新)、**`data/operation_repo.py`**、**`ui/undo.py`**、`core/__init__.py`、`app_shell.py`、`sidebar.py`、`icons.py`、`build.spec` | `core/report.py`(泛化) 或 `core/history_report.py`(新)、`ui/pages/history_page.py` |
| 数据库变化 | **否**（复用 `history`/`operations`；偏好走 settings KV） | **是**（新增 operation type / 列 / 表 + 迁移） | **否**（纯读取） |
| 新 UI 页面 | **是**（1 个） | **是**（1 个） | **否**（现有页面加按钮） |
| 新核心服务 | **是**（size 分桶 → 采样 → 全量 SHA-256 漏斗） | **是**（模板引擎 + 冲突校验） | **是但极小**（1 个纯函数） |
| 新测试层 | **是**（`tests/test_duplicates.py`） | **是**（`tests/test_rename.py`） | **是**（`tests/test_history_report.py`） |
| 影响 V1.2-A 行为 | 否 | 低-中（共享 `operations` / `run_undo` 语义需向后兼容） | **低**（需保证 F3 现有 7 测试零回归） |
| undo / safety / data-loss 风险 | **中**（必须"每组至少保留一份"；哈希失败降级为跳过） | **中-高**（原地改名更难撤销；保留名/非法字符/冲突需预览期拦截） | **极低**（纯只读 + 写单一用户指定文件） |
| 影响 Release packaging | **是**（`build.spec` hiddenimports） | **是**（`build.spec` hiddenimports） | **否** |

**跨候选的共同约束（重要）**

1. **导航注册面是瓶颈。** `tests/test_navigation.py::test_every_page_nav_entry_is_registered_and_routable` 要求**每个页面型导航项都必须在 `app_shell._TITLES` 中有标题**。因此新增导航项 = 同时改 `sidebar._NAV` + `app_shell._TITLES` + `app_shell._pages` —— 而这三处**两处是混合文件**。
2. `tests/test_navigation.py` 锁的是"**必需集合 + 相对顺序**"，不是绝对条数，因此**新增导航项不会直接破坏该锁**（新项只要不改变 `REQUIRED_NAV` 的相对顺序即可）。这是 V1.2-A-CLOSURE 有意留下的兼容性。
3. `tests/test_appshell.py:67` 断言 `("home","organize","custom","history","settings")` 必须可路由 —— **`home` / `custom` 两个不可达页面的注册是硬契约**，任何"清理死代码"的动作都会打破它。

---

## 8. Testing strategy

### 8.1 现有测试基线（实测）

| 树 | 结果 |
|---|---|
| 提交树（V1.2-A，96 tests） | **96 passed** |
| 工作区（含 PHASE 1.2，107 tests） | **107 passed** |

按文件分布（工作区）：

```
15 test_custom_rules     11 test_large_files      8 test_update        4 test_security
15 test_about_update     11 test_analysis         8 test_navigation    4 test_p2_coverage
 9 test_reliability       7 test_report           5 test_windows_paths 2 test_combined_path_v11
                          7 test_empty_folders                          1 test_core
```

### 8.2 V1.2-B 的测试分层要求（建议）

| 层 | 内容 | 必须性 |
|---|---|---|
| **回归锁（不可绕过）** | 全量 `pytest`；`tests/test_navigation.py`（8）；`tests/test_appshell.py`；F3 的 `tests/test_report.py`（7） | **必须** |
| **单元测试** | 新 scope 的核心纯逻辑（报告源构造、schema 字段、边界：空历史 / 单条 / 大量记录） | **必须** |
| **契约测试** | `REPORT_SCHEMA` 与 `CSV_COLUMNS` / `CSV_SECTIONS` 保持稳定；`rules_fingerprint` 纯度 | **必须** |
| **GUI 冒烟** | offscreen 构建 → 历史页 → 导出 → 落盘校验（沿用 `D:/Temp/dc_smoke_f{1..4}.py` 模式，新增 `dc_smoke_b*.py`） | **必须** |
| **编译 / 导入** | `compileall src` + 逐模块 import | **必须** |
| **索引 / 提交树双跑** | 若涉及提交，需在**索引导出树**与**提交树**分别跑全量 | 视阶段要求 |

### 8.3 测试环境注意事项（本阶段实测）

- 需要 `pytest` 的解释器：**`D:/Temp/dc_verify_venv/Scripts/python.exe`**（Python 3.13.14 / pytest 9.1.1）。
  受管 Python（`3.11.9` / `3.13.12`）**未安装 pytest**。
- 必须设 `QT_QPA_PLATFORM=offscreen`（GUI 测试）。
- `tests/conftest.py` 的 autouse fixture 会把 DB 重定向到各测试模块自己的 `_TMP_HOME`；
  每个测试模块**必须**在模块级定义 `_TMP_HOME`。
- 冒烟脚本必须可通过 `DC_PROJ` 环境变量改路径，否则无法对提交树 / 导出树运行。

---

## 9. Implementation prerequisites

> 以下为**动工前必须满足**的前置条件，按阻塞强度排序。

| # | 前置条件 | 阻塞强度 | 说明 |
|---|---|---|---|
| **P1** | **PHASE 1.2 必须先收尾提交** | **强阻塞（对候选 1/2）** | `src/ui/app_shell.py` 与 `src/ui/widgets/sidebar.py` 是**混合文件**，当前同时携带未提交的 PHASE 1.2 改动。任何新增导航项的 V1.2-B 功能都会再次触发"逐 hunk 分离"问题——这正是本阶段要避免的。**候选 3 不受此阻塞**（不碰这两个文件）。 |
| **P2** | `ui/features.py` 必须先解除 PHASE 1.2 占用 | 强阻塞（对 D7） | 该文件是 PHASE 1.2 已修改文件；在它被提交之前，任何注册中心同步都会混入 PHASE 1.2。 |
| **P3** | 测试解释器与运行约定固定 | 中 | 使用 `D:/Temp/dc_verify_venv/Scripts/python.exe` + `QT_QPA_PLATFORM=offscreen`；受管 Python 无 pytest。 |
| **P4** | 明确 `home` / `custom` 的注册契约 | 中 | `tests/test_appshell.py:67` 与 `tests/test_navigation.py::test_off_nav_pages_still_registered` 双重锁定：这两个不可达页面**必须继续注册**。任何"顺手清理"都会破锁。 |
| **P5** | 若选候选 2：先出数据层迁移设计 | 中（条件性） | `operations` 表新增 rename 语义需显式迁移（`_SCHEMA` 用 `CREATE TABLE IF NOT EXISTS`，不会自动加列）。 |
| **P6** | 若选候选 1：先定义"每组至少保留一份"的不可绕过约束 | 中（条件性） | 必须是硬性断言 + 测试锁定，而非 UI 层建议。 |
| **P7** | 明确 V1.2-B 的提交边界 | 中 | 建议沿用 V1.2-A-CLOSURE 的纪律：显式路径 `git add`（**禁止 `git add .`**）、混合文件逐 hunk 分离、`git diff --cached --check`、提交后导出独立复验。 |
| **P8** | 更新 `docs/LEGACY_SURFACE_INVENTORY.md` 的过期快照 | 低 | 其记录的 `_pages` 6 键 / 侧栏 4 入口已过期（现为 9 键 / 7 入口）。**属文档更新，需 Owner 授权**。 |

---

## 10. 下一阶段需要 Owner 明确授权的事项

| # | 事项 | 需要的授权 |
|---|---|---|
| **A1** | 是否采纳 §5 建议的 **V1.2-B = 报告导出能力收口** scope | 明确 `APPROVE` / `REJECT` / `MODIFY` |
| **A2** | **PHASE 1.2 收尾提交**（4 个已修改 + 4 个未跟踪产物） | 独立阶段授权（这是候选 1/2 与 D7 的强前置） |
| **A3** | `docs/PHASE_R5.*.md` 两份文档的归属（提交 / 归档 / 保持未跟踪） | 明确处置 |
| **A4** | `.workbuddy-ai/` 是否加入 `.gitignore` | 明确处置（本阶段禁止修改 `.gitignore`） |
| **A5** | 死代码处置（796 行 + `ui/styles.py`）是否单独立项 | 明确 `DEFER` / `SCHEDULE` |
| **A6** | 测试去重（`test_navigation.py` ↔ `test_large_files.py` 概念重叠）是否单独立项 | 明确 `DEFER` / `SCHEDULE` |
| **A7** | 重复文件查找是否立项为 **V1.2-C** | 明确 `DEFER` / `SCHEDULE` |
| **A8** | 注册中心 / README 与产品事实同步（G5）的排期 | 明确排期（受 P2 阻塞） |
| **A9** | 本审计报告自身的处置（是否提交 / 是否归档） | 明确处置 |
| **A10** | 是否授权进入 **PHASE V1.2-B-IMPLEMENTATION** | 未授权前**不得动工** |

---

## 附：本阶段实际写入的文件

本阶段唯一写入的文件是**本报告本身**（新建、未跟踪）：

```
docs/PHASE-V1.2-B-PREPARATION-AUDIT.md   (新建)
```

未修改任何源码 / 测试 / 配置 / `.gitignore`；未删除任何代码；未做测试重构或去重；
未执行任何 Git 写操作（无 add / commit / push / tag / merge / rebase / amend / squash）；
未开始实现 V1.2-B；未触碰 PHASE 1.2 工作区内容。

外部临时目录仅用于**只读导出与测试**，不在项目内：

```
D:/Temp/dc_v12b_probe/        ← git archive HEAD 的只读导出（跑 96 tests）
D:/Temp/dc_v12b_probe_home/   ← 运行期 AppShell 探针的隔离 DB 目录
```

---

**V1.2-B-PREPARATION COMPLETE**
**IMPLEMENTATION NOT AUTHORIZED**
**HARD STOP**
