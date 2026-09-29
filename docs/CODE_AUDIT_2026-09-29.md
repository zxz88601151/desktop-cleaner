# 代码审计报告 — Desktop Cleaner 桌面文件整理助手

| 项 | 值 |
|---|---|
| 被审版本 | **1.1.1**（stable） |
| 审计日期 | 2026-09-29 |
| 审计范围 | `main.py` + `src/`（core / data / ui / update / utils，55 个 .py）+ `tests/` + `tools/` + `build.spec` / `requirements.txt` |
| 审计方法 | 全量静态审查 + 实跑测试（`pytest` 59 passed）+ offscreen GUI 冒烟 |
| 审计环境 | Python 3.13.12 / PySide6 6.11.2 / Windows |
| 结论 | **工程质量高于同类个人项目**：分层清晰、安全模型扎实、测试有真实断言。本轮修复 8 处已确认缺陷，无 P0 级安全漏洞。 |

---

## 一、结论摘要

这个项目的"骨架"很稳，值得肯定：

- **安全模型是真正的护城河**，且是"默认安全"而不是"事后补丁"：只移动不删除、冲突自动重命名、两阶段落库 + 启动对账、更新 URL 的 HTTPS + Host 白名单 + fail-closed。
- **分层纪律好**：`core`（纯逻辑）/ `data`（SQLite）/ `ui`（PySide6）/ `update`（纯函数 + Qt 胶水）边界基本清晰，`update/checker.py`、`version.py`、`decision.py`、`manifest.py` 完全 Qt-free，可单测。
- **工程化完整**：发布校验脚本、SHA256 契约、依赖基线文档、47→59 项测试。

本轮审计发现的问题以**一致性、健壮性、可维护性**为主，只有 3 处会真正影响用户/稳定性（P1），且已全部修复。

| 级别 | 数量 | 说明 |
|---|---|---|
| P0 安全 | 0 | 无 |
| P1 功能/稳定性 | 3 | 已全部修复（见 §二） |
| P2 一致性/健壮性 | 6 | 5 项已修复，1 项建议后续处理 |
| P3 可维护性/性能 | 9 | 记录建议，不阻塞发布 |

---

## 二、P1 级缺陷（会真正影响用户 / 稳定性）— 已修复

### P1-1 更新检查"离线误报为最新"，且失败会吃掉 24h 节流窗口

**位置**：`src/update/manager.py::_on_result` / `start_check`，`src/ui/app_shell.py::_on_no_update`

**问题**：`fetch_manifest()` 在**任何**失败（断网 / 超时 / TLS / JSON 损坏）时返回 `None`，而 manager 把 `None` 和"已是最新"合并成同一个 `no_update` 信号：

```python
if not manifest or evaluate(self._current, manifest) == LEVEL_NONE:
    self.no_update.emit()
```

于是设置页/About 页手动点"检查更新"，**离线时也会弹出"当前已是最新版本"**——这是 README §8.2 里自己记录的已知缺陷。更隐蔽的是 `start_check()` 在**发起请求前**就调用了 `_mark_checked()`，所以一次失败会把 24h 节流窗口也消耗掉：用户断网启动一次，接下来一整天都不会再检查。

**影响**：用户被误导（以为是最新，实际根本没检查到）；且失败后无法及时重试。

**修复**：
- `UpdateManager` 新增独立信号 `check_failed`，`None` → 只发 `check_failed`，**不再发** `no_update`；真正的"已最新"才发 `no_update`。
- 节流窗口改为**只在 fetch 成功时**标记（`_mark_checked()` 移入 `_on_result` 成功分支），失败下次启动自动重试。
- `app_shell` 新增 `_on_check_failed`：后台检查仍静默，手动检查明确提示"检查更新失败：无法连接更新服务，请稍后重试。"——与 About 页原本就正确的 fail-closed 语义对齐。
- 顺带为 worker 补上 `finished → deleteLater`，避免 QThread 累积。

**验证**：`tests/test_update.py::test_manager` 新增 case 4（失败不消耗节流）+ case 3 改为断言 `check_failed`；offscreen 冒烟确认断网只发 `check_failed`、不发 `no_update`。

### P1-2 `rules.py` 扩展名规则存在重复键，`.ts` 被静默劫持

**位置**：`src/core/rules.py::DEFAULT_RULES`

**问题**：`DEFAULT_RULES` 是一个 dict 字面量，其中两个扩展名被声明了两次：

```python
"mpg": "videos", "mpeg": "videos", "ts": "videos", "3gp": "videos",   # 视频
...
"py": "code", "js": "code", "ts": "code", "tsx": "code", "jsx": "code",  # 代码
```

Python 对 dict 字面量的重复键**取最后一次**，因此 `.ts` 实际落到了 **代码** 分类——所有 MPEG-TS 视频文件（录屏、摄像机、下载视频常见格式）都会被归进"代码"文件夹。另有 `"wav"` 重复声明（恰好同为 audio，无功能影响，但属噪音）。

**影响**：视频文件被错误分类；对"非技术用户"目标人群尤其明显。

**修复**：显式消除歧义——`.ts` 归属 **视频**（保留 `mts`/`m2ts` 补充），从 code 行移除；删掉重复的 `wav`；并加了大段注释说明这是一次**有意的、单点可切换**的裁决（若受众转为开发者，改一行即可）。同时新增源码级回归护栏 `test_rules_no_duplicate_extensions`，从根上防止重复键再次悄悄出现。

### P1-3 首页撤销用局部变量持有 Worker，QThread 可能被 GC 后崩溃

**位置**：`src/ui/pages/dashboard_page.py::_undo_latest`

**问题**：其他页面（organize/history）都写成 `self._worker = Worker(...)`，唯独首页用了局部变量：

```python
worker = Worker(lambda p, l: run_undo(latest["id"], p, l))
worker.start()
```

函数返回后 `worker` 引用计数归零，Python 可能回收其 C++ 对象，而线程仍在运行 → Qt 报 `QThread: Destroyed while thread is still running`，极端情况下直接崩溃。这是典型的"偶发、难复现"崩溃来源。

**修复**：改为 `self._worker` 持有强引用，并补 `_busy()` 防重入。

---

## 三、P2 级问题（一致性 / 健壮性）

### P2-1 `history_repo.get_stats` 文档与 SQL 不一致 — 已修复
`docstring` 写 "total_files: status='done'"，但 SQL 实为 `status IN ('done','undone')`。经核对 `tests/test_dashboard.py` 明确断言 *"undone runs still count toward runs total"*，即**行为是有意的**，错的是文档。已把 docstring 改写为准确描述（"累计活动量"而非"当前已整理量"），**不动行为**，避免破坏既有契约。

### P2-2 `tools/release_validate.py` 泄漏文件句柄 — 已修复
`tempfile.mkstemp(...)[1]` 丢弃了返回的 fd，每次远程校验泄漏一个句柄。已改为取 `(fd, name)` 并立即 `os.close(fd)`。

### P2-3 `build.spec` 的 `hiddenimports` 缺项 — 已修复
PHASE 1.2 新增的 `ui.pages.large_files_page` 以及 `ui.widgets.sidebar`、`ui.widgets.score_ring`、`ui.icons`、`utils.paths`、`utils.errors` 都未列入 `hiddenimports`。虽然 PyInstaller 的自动分析通常能兜住（这些都是普通 import），但 spec 里其它页面都显式列了，**不一致本身就是隐患**——一旦将来改成动态导入就会漏打包。已补齐。

### P2-4 更新信息校验"双轨制" — 建议后续处理
同一份 manifest 存在两套校验路径：`update/constants.py::validate_manifest_basics`（About 页用）与 `update/manifest.py::parse_manifest`（checker 用）。两者规则相近但不完全一致（例如 `validate_manifest_basics` 不校验 `minimum_supported_version` 合法性，而 `parse_manifest` 会）。**建议**统一为单一入口（保留 `parse_manifest` 作为唯一权威，`validate_manifest_basics` 改为对其的薄封装）。本轮未动，因涉及跨模块契约、需单独验证。

### P2-5 `UpdateDialog` 与 `decision.evaluate` 各自实现"强制更新"判定 — 建议后续处理
`update_dialog.py` 内联重算了 forced 逻辑（`minimum_supported_version` + `is_older_than`），与 `decision.evaluate` 的 FORCE 分支重复。两处未来可能漂移。建议 `UpdateDialog` 直接接收 `evaluate()` 的级别结果。

### P2-6 `checker.fetch_manifest` 只返回 `None`，丢失失败原因 — 已缓解
P1-1 的根因之一是"失败原因不可区分"。本轮通过在 manager 层把 `None` 单独归类为 `check_failed` 解决了**用户可见**的问题；若将来要区分"断网 / 服务器 5xx / 数据损坏"并给出不同提示，需要让 `fetch_manifest` 返回结构化结果。属于可选增强。

---

## 四、P3 级问题（可维护性 / 性能 / 死代码）

### P3-1 死代码约 1000 行（**需产品决策，本轮未删**）
经 offscreen 实测确认，以下模块**在运行期不可达**：

| 模块 | 行数 | 状态 |
|---|---|---|
| `ui/pages/tools_page.py` + `ui/coming_soon.py` + `ui/features.py` | ~364 | "更多工具"已从导航移除（Decision 02），三者互相引用但无人调用 |
| `ui/pages/dashboard_page.py` | 240 | 实测 sidebar 无 `home` 入口（导航仅 organize/large/history/settings + about），页面被构造但不可达 |
| `ui/pages/custom_page.py` | 192 | 注释明示已从导航移除，但仍在 `AppShell._pages` 中实例化 |

冒烟输出为证：`pages = ['custom','history','home','large','organize','settings']`，而 `sidebar nav ids = ['about','history','large','organize','settings']`。

**建议**：若这些是"暂时下架、后续恢复"，则保留并在 `features.py` 里标注；若确为弃用，删除可显著降低心智负担。**这是产品意图问题，我不擅自删除。**

### P3-2 `core` → `data` 分层倒置
`src/core/scanner.py::scan` 内 `from data.database import data_dir` 做"禁止整理应用自身数据目录"的保护。这让本应纯净的 core 反向依赖 data。**建议**：把"禁止目录"作为可选参数由调用方注入（`scan(..., forbidden_dir=...)`），或把该守卫上提到 data/ui 层。

### P3-3 主题模块三重间接
`ui/theme_manager.py` 与 `ui/themes.py` 都只是 shim，真正实现在 `ui/theme/theme_manager.py` / `ui/theme/themes.py`；另有 legacy `ui/styles.py`。为兼容迁移而保留，可理解，但 `ui/themes.py`、`ui/theme_manager.py`、`ui/styles.py` 三个"空壳"长期看是噪音。**建议**迁移收口后删除 shim，统一 import 路径。

### P3-4 页面间重复样板
`organize_page` / `large_files_page` / `dashboard_page` / `custom_page` 各自实现了一遍 `_browse()`、`_valid_root()`、`_load_settings()`（读 `last_source` / `recursive` / `mode`）、`_busy()/_set_busy()`。**建议**抽一个 `FolderPickerRow` / `PageBase` 基类或 mixin，消除 4 份重复。

### P3-5 扫描每文件两次 `stat`
`scan()` 先 `entry.is_file()`（一次 stat）再 `f.stat().st_size`（第二次）。大目录下是 2× 系统调用。**建议**合并为一次 `os.stat` + `stat.S_ISREG`。

### P3-6 设置仓库每次调用新开连接
`settings_repo.get/set` 每次 `get_connection()`（含 3 条 PRAGMA）。热路径（如 dashboard 刷新、节流判断）会频繁开关连接。**建议**引入按线程的连接复用或内存缓存，`set` 时写穿。

### P3-7 `about.py` 硬编码功能列表，与 Feature Registry 并存
`about.py::_FEATURES` 手写 5 条卖点，而 `ui/features.py` 号称"产品能力唯一事实来源"。二者不一致。**建议**：About 的卖点要么从注册表派生，要么明确注释为"面向用户的营销文案，非能力清单"。

### P3-8 `requirements.txt` 缺测试依赖
只有 PySide6 / PyInstaller，没有 `pytest`（README §7.3 却指导跑 pytest）。**建议**补 dev 依赖或拆 `requirements-dev.txt`。

### P3-9 `main.py` 使用 Qt6 已废弃的 High-DPI 属性
`AA_EnableHighDpiScaling` / `AA_UseHighDpiPixmaps` 在 Qt6 中已是 no-op（高 DPI 恒开）。无害，但属死代码，可删以免误导。

---

## 五、安全复核（结论：通过）

| 检查项 | 结论 | 依据 |
|---|---|---|
| 更新源仅 HTTPS + Host 白名单 | ✅ | `constants.is_allowed_download_url` 拒绝 http / 内网 / localhost / 非 443 / userinfo |
| 更新失败 fail-closed | ✅（本轮补齐） | 原 manager 存在误报，已修；About 页原本正确 |
| 不自动下载 / 替换 EXE | ✅ | Option B，仅提供用户主动的下载入口 |
| 只移动不删除、不覆盖 | ✅ | `_unique_target` 冲突重命名；`move_items` 逐文件校验 |
| 崩溃可恢复 | ✅ | pending 两阶段落库 + `reconcile_pending` 启动对账 |
| 禁止整理应用自身数据目录 | ✅ | `scanner` 显式 `ValueError` |
| 跳过系统 / 隐藏文件 | ✅ | `_SYSTEM_FILES` + `GetFileAttributesW` 隐藏位 |
| Windows 长路径（>260） | ✅ | `utils.paths.win_long` 统一 `\\?\` 前缀 |
| 数据不出本机 | ✅ | 无上传逻辑；网络仅更新检查 |

**遗留安全项（非代码缺陷，属发布工程）**：EXE 未签名、无 Authenticode 校验，SmartScreen 会告警；`update/integrity.py` 的 SHA-256 原语已就绪但尚未接入自动更新（Option A）。建议在 v1.2+ 引入代码签名证书。

---

## 六、本轮精细化改动清单

> **重要更正（PHASE 0 基线审计补充）**：经 `git diff` 逐 hunk 核对，进入本轮之前**已存在**的工作区改动共 **4 个文件**（而非此前记录的 3 个）——`src/core/scanner.py`、`src/ui/features.py`、`src/ui/widgets/sidebar.py`，**以及 `src/ui/app_shell.py`**。它们同属未提交的 **PHASE 1.2「大文件发现」** 功能（新增 `large_files_page.py` / `test_large_files.py` / 3 份 PHASE 文档，均未提交）。
>
> 其中 **`src/ui/app_shell.py` 是混合文件**：它的 5 个改动 hunk 里有 3 个属 PHASE 1.2（`import LargeFilesPage`、`"large": "大文件分析"` 标题、`"large": LargeFilesPage()` 页面注册），只有 2 个属本轮（`check_failed` 接线 + `_on_check_failed` 方法）。基线提交时已**只暂存本轮那 2 个 hunk**，未夹带既有改动。

| 文件 | 改动 |
|---|---|
| `src/update/manager.py` | 新增 `check_failed` 信号；失败不再冒充"已最新"；节流仅成功时消耗；worker `deleteLater` |
| `src/ui/app_shell.py`（**部分**，混合文件） | 接入 `check_failed`，新增 `_on_check_failed`（后台静默 / 手动明确报错）。**同文件的 3 个 PHASE 1.2 hunk 属既有改动，本轮未纳入提交。** |
| `src/core/rules.py` | 消除 `.ts` / `.wav` 重复键；`.ts` 显式归视频；补 `mts`/`m2ts` |
| `src/ui/pages/dashboard_page.py` | 撤销 Worker 改 `self._worker` 强引用 + `_busy()` 防重入 |
| `src/data/history_repo.py` | `get_stats` docstring 与 SQL 行为对齐（不改行为） |
| `tools/release_validate.py` | 关闭 `mkstemp` 泄漏的 fd |
| `build.spec` | 补齐 `hiddenimports`（large_files_page / widgets / icons / utils.paths / utils.errors） |
| `tests/test_core.py` | 新增回归护栏 `test_rules_no_duplicate_extensions` |
| `tests/test_update.py` | case 3 改为断言 `check_failed`；新增 case 4（失败不消耗节流） |

**验证结果**：`pytest tests/` → **59 passed**（含 2 项新增护栏）；offscreen GUI 冒烟通过（AppShell 正常构建、断网只发 `check_failed`）。

---

## 七、需你拍板的事项

1. **死代码（P3-1）**：`tools_page` / `coming_soon` / `features` / `dashboard_page` / `custom_page` 约 1000 行不可达——**保留待恢复**还是**删除**？
2. **`.ts` 归属（P1-2）**：我按"面向非技术用户"裁决为**视频**。若你希望 `.ts` 归**代码**，改 `rules.py` 一行即可（注释已标明）。
3. **更新校验双轨（P2-4/P2-5）**：是否授权我下一轮统一为单一入口？
4. **代码签名 / 自动更新 Option A**：是否纳入 v1.2 计划？
