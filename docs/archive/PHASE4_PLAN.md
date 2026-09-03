# Desktop Cleaner Phase 4 Implementation Plan

> 本文件为 **Phase 4 计划**（只读审计 + 当前源码核查后产出），**未修改任何代码**。
> 目标：闭环 P2 剩余问题，建立 Phase 5 Release Candidate 的稳定、可重复、可验证发布基线。
> 硬约束（全程遵守）：不削弱 P0 安全机制；不改 `operations`/`history` 表结构；不改 core 业务规则（分类/路径/撤销语义）；不重构 UI；不新增功能（AI/自动整理/通知/定时任务等）。

---

## 核查基线

- 已重读：`AUDIT_REPORT.md` / `REMEDIATION_PLAN.md` / `PHASE2_REPORT.md` / `PHASE3_REPORT.md`
- 已通读当前真实源码：`src/utils/{logger,paths,errors}.py`、`src/core/{organizer,scanner}.py`、`src/data/{database,operation_repo}.py`、`src/ui/{theme_manager,themes}.py`、`requirements.txt`、`build.spec`、`build.bat`、`.gitignore`、工作树与 `tests/`
- P0/P1 现状：Phase 2 P0 全 PASS；Phase 3 P1 除 P1-5（长路径）为 CONDITIONAL 外全 PASS。本次不回归 P0/P1 逻辑，仅在其上做 P2 加法/卫生。

---

## P2-1 结构化日志增强

| 项 | 内容 |
|---|---|
| 当前状态 | `utils/logger.py` 格式为 `%(asctime)s [%(levelname)s] %(message)s`；`organizer.move_items` 已在失败时写 `MOVE FAILED src=.. tgt=.. type=.. msg=..`（含 operation/source/target/error_type/error_message）。**缺失**：(a) 格式未含 `module` 字段；(b) 生命周期缺 启动/扫描/撤销 的 INFO 记录（异常已覆盖）。 |
| 代码位置 | `src/utils/logger.py`、`src/core/organizer.py`、`src/core/scanner.py`、`src/ui/undo.py`、`main.py` |
| 是否修改 | **需要（最小加法，不重写）** |
| 准备修改 | 1) formatter 增加 `%(name)s`（module），保持 `时间 [级别] 模块 消息` 机器+人工可读；2) 在 `main.py` 启动 + `reconcile_pending` 结果写 INFO；3) `scanner.scan` 入口/出口写 INFO（root/mode/recursive/文件数，纯只读副作用）；4) `ui/undo.run_undo` 写 undo 开始/完成(含失败数) INFO；5) `move_items` 末尾补一行整理汇总 INFO（moved/failed）。 |
| 风险 | 极低。仅新增 INFO 日志与格式字段，不改变任何文件操作/DB 写入/业务分支。 |
| 测试方式 | 现有测试不受影响；新增 1 个 `test_logging_format` 断言 formatter 含 `name` 字段且一条记录可被解析出 time/level/module。 |

---

## P2-2 测试覆盖增强

| 项 | 内容 |
|---|---|
| 当前状态 | 已有：`test_core`（扫描/整理/持久化/幂等/撤销/碰撞/日期）、`test_security`（P0-1~4）、`test_reliability`（WAL/批量/去重/失败明细/异常传播）、`test_windows_paths`（长路径 helper）。**缺口**（审计 12 项中尚未真实验证）：① 源文件不存在时 organize 记录 failed 且不崩溃 ③ 撤销部分失败（已覆盖，不重复）④ 目标已存在碰撞（已覆盖）⑦⑧⑨⑩⑪（已覆盖）。待补：源缺失、旧库(rollback-journal)WAL 兼容升级、启动 reconcile 将 `running`→`done`。 |
| 代码位置 | 新增 `tests/test_p2_coverage.py` |
| 是否修改 | **需要（新增文件，不改动已有测试）** |
| 准备修改 | 新增用例（全部用 `tmp_path` + `DESKTOP_CLEANER_HOME` 隔离，不碰真实数据）：T1 `move_items` 对源已删除的文件 → 记 `failed`、不抛、其余继续；T2 用旧式 rollback-journal DB（非 WAL）经 `get_connection` 打开 → 验证 WAL 自动升级、表/索引可用、可正常写入读取；T3 构造一条 `running` history 含 pending+moved 混合 ops → `reconcile_pending()` 结算为 `done` 且 moved 数正确。 |
| 风险 | 极低。纯新增测试；沿用现有测试的环境隔离模式。 |
| 测试方式 | `python tests/test_p2_coverage.py` 全 PASS；不重复已有断言。 |

---

## P2-3 Windows 长路径真实验证

| 项 | 内容 |
|---|---|
| 当前状态 | Phase 3 为 **CONDITIONAL**：`\\?\` 前缀字符串变换已验证；真实 >260 字符**文件系统移动**在本沙箱卷返回 `WinError 123`（卷语法限制）未实跑。 |
| 代码位置 | `src/utils/paths.py`（`win_long`/`safe_exists`/`safe_is_file`）、`src/core/organizer.py`（`move_items` 已用 `win_long`） |
| 是否修改 | **不修改代码**；仅做真实环境验证实验 |
| 准备修改 | 编写一个独立验证脚本（非 skip），在**真实 Windows 盘符**（非 pytest 临时卷）下：创建深度 >260 字符路径 → `scan` → `plan` → `organize`（真实 `shutil.move` + `win_long`）→ 校验目标存在/源消失 → `undo` 还原 → 校验不覆盖。记录每一步真实结果。 |
| 风险 | 若本环境卷仍不支持 `\\?\` 真实移动 → **保持 CONDITIONAL**，如实记录 `WinError` 原文，**绝不伪造 PASS、绝不为凑 PASS 改测试 skip**。 |
| 测试方式 | 真实运行脚本；成功则改 PASS 并附证据，失败则维持 CONDITIONAL 并附错误原文。 |

---

## P2-4 仓库卫生

| 项 | 内容 |
|---|---|
| 当前状态 | 工作树含明确临时/构建产物：`_*.txt`（×6：`_launch_check/_paths/_probe/_py/_results/_test_out`，旧会话探针/输出）、`dist_old_*`(×5)、`build_old_*`(×1)、根/`src`/`tests` `__pycache__`、`_tmp_home/`(28KB，仅含测试 sandbox HOME 的 `data/desktop_cleaner.db`)。`data/`（项目根）是**真实开发库**（源码运行时 DB 落此处，0 字节空库），**不可删**。`dist/`（当前构建 exe）保留。`design/`（截图交付物）保留。`.gitignore` 缺：`_tmp_home/`、`_*.txt`、`.pytest_cache/`、`*.db-wal`、`*.db-shm`、`build_old_*/`、`dist_old_*/`。 |
| 代码位置 | 工作树 + `.gitignore` |
| 是否修改 | **需要（清理 + 补 .gitignore）** |
| 准备修改 | 1) 删除：`_*.txt`、`dist_old_*`、`build_old_*`、各 `__pycache__`（字节码可重建）、`_tmp_home/`（测试 sandbox HOME，非用户数据，删除前会 `ls` 确认仅含测试 db）；2) **保留**：`data/`、`dist/`、`design/`、`.git`、所有源码与报告 md；3) `.gitignore` 增补上述忽略项（含 WAL 运行时文件 `*.db-wal`/`*.db-shm`）。 |
| 风险 | 低。删除项均为可重建/测试产物；删除前逐项 `ls` 核验内容，绝不删 `data/`、`dist/`、`design/`、源码。若对任一文件归属存疑 → 保留并在报告中说明。 |
| 测试方式 | 清理后 `git status` 核验工作树；`python -m compileall` 仍 PASS；功能测试零影响（仅删临时/缓存）。 |

---

## P2-5 构建可复现性

| 项 | 内容 |
|---|---|
| 当前状态 | `requirements.txt` 仅 `PySide6>=6.7.0`，**缺 `pyinstaller`**；`build.bat` 内联 `pip install pyinstaller`（永远拉最新）→ 换机器/换时间结果不一致。本环境**未安装** pyinstaller/PySide6，无法自动探测构建机真实版本。 |
| 代码位置 | `requirements.txt`、`build.bat` |
| 是否修改 | **需要（最小锁版本，不升级/不新增依赖）** |
| 准备修改 | 1) `requirements.txt`：保留 `PySide6==6.7.0`（取既有下限为可复现基线），新增 `pyinstaller==<VER>`；2) 因构建机版本本环境不可测，pyinstaller 版本**采用保守已知可用值并在报告中明确标注「须与产出当前 `dist/DesktopCleaner.exe` 的构建机版本一致，请核对后修正」**，不谎称已验证。3) `build.bat` 改为从 `requirements.txt` 安装（`pip install -r requirements.txt`），不再单独 `pip install pyinstaller`。 |
| 风险 | 低。仅约束依赖版本；不改动运行环境、不引入新包。pyinstaller 具体版本号需用户在构建机核对（诚实标注，非猜测为已验证）。 |
| 测试方式 | `pip install -r requirements.txt` 在构建机可复现安装；本报告标注待核对项。 |

---

## P2-6 build.bat 与 build.spec 一致性

| 项 | 内容 |
|---|---|
| 当前状态 | `build.bat` 完全内联 `pyinstaller --name ... --onefile --windowed --noconfirm --clean --paths src main.py`，**未引用 `build.spec`**，因此丢失 spec 中的全部 `hiddenimports`（含 `ui.undo`、`utils.*` 等）→ 两条打包路径产物不一致，且易因漏 import 在 frozen 后崩溃。 |
| 代码位置 | `build.bat`、`build.spec` |
| 是否修改 | **需要（最小，统一为单一事实源）** |
| 准备修改 | 将 `build.bat` 的打包命令改为 `pyinstaller build.spec`（spec 已含 name/onefile/windowed/hiddenimports/codesign 占位）。保留 `pip install -r requirements.txt` 前置。可选：在 exe 生成后追加**条件签名**步骤（`if defined CERT ... signtool sign ...`），无证书则跳过，不改变现有 `codesign_identity=None` 行为。 |
| 风险 | 低。命令行等价迁移；spec 已验证隐藏导入完整。 |
| 测试方式 | 仅静态核对：`.bat` 与 `.spec` 的 name/onefile/windowed/hiddenimports 一致；Phase 5 才真正执行打包。 |

---

## P2-7 shim / 兼容层收敛

| 项 | 内容 |
|---|---|
| 当前状态 | `src/ui/theme_manager.py`、`src/ui/themes.py` 为转发 shim（指向 `ui.theme.theme_manager` / `ui.theme.themes`）。经 grep 确认：`ui.theme_manager` 被 **15+ 真实模块**引用（`app_shell`、`dashboard`、`styles`(间接)、`custom_page`、`dashboard_page`、`organize_page`、`settings_page`、`widgets/controls`、`widgets/score_ring`、`ui/undo`、`ui/__init__` 等）；`ui.themes` 被 `styles.py` 引用。删除任一即触发 ImportError 启动失败。 |
| 代码位置 | `src/ui/theme_manager.py`、`src/ui/themes.py`、`src/ui/theme/*` |
| 是否修改 | **NO ACTION REQUIRED — 保留并记录** |
| 准备修改 | 不做删除。原因：shim 仍是真实实现的可达路径，删除需改写 15+ 处 import（属 UI 迁移重构，超出 Phase 4 范围且回归风险高）。符合「删除风险较高 → 保留并记录」。 |
| 风险 | 无（保持现状）。 |
| 测试方式 | 不改动；`compileall` 保持 PASS。 |

---

## 数据库安全（Phase 4 红线）

- 不改表结构、不删字段、不改语义、不强制迁移旧库。
- `*.db-wal`/`*.db-shm` 为 WAL 正常运行产物，仅加入 `.gitignore` 忽略，不删除、不视为垃圾。
- 旧库（含 rollback-journal 库）经 `get_connection` 打开即自动升级 WAL，向后兼容（P1-1 已容错降级）。

---

## 全量回归与 RC Gate（实施阶段末尾执行）

1. `python tests/test_core.py` → 期望 ALL PASSED（P0/P1 零回归）
2. `python tests/test_security.py` → 期望 ALL P0 PASSED
3. `python tests/test_reliability.py` → 期望 ALL P1 PASSED
4. `python tests/test_windows_paths.py` → 期望 PASS（真实移动依环境，否则 CONDITIONAL）
5. `python tests/test_p2_coverage.py`（新增）→ 期望 PASS
6. `python -m compileall -q src main.py` → 期望 PASS
7. RC Gate 静态验收：启动/扫描/预览/整理/撤销链路由测试覆盖；异常可显示（P1-6）、日志可记录（P2-1）、DB 可保存（WAL）、失败可追踪（P1-4）均已具备。

---

## 预计交付

- 修改文件：`src/utils/logger.py`（格式）、`src/core/scanner.py`（scan INFO 日志）、`src/ui/undo.py`（undo INFO 日志）、`main.py`（启动日志）、`src/core/organizer.py`（汇总日志，加法）、`requirements.txt`、`build.bat`、`.gitignore`
- 新增文件：`tests/test_p2_coverage.py`、`tests/test_logging_format.py`（或并入 p2_coverage）
- 删除（仅临时/缓存/旧构建）：`_*.txt`、`dist_old_*`、`build_old_*`、`__pycache__`(根/src/tests)、`_tmp_home/`
- 报告：`PHASE4_REPORT.md`

## 预期判定

**READY WITH CONDITIONS** —— P2-1/2/4/5/6/7 实做并验证；P2-3 维持 CONDITIONAL（除非本环境真实卷允许 >260 移动）；代码签名（P1-4，需外部证书）仍属发布阻断项，留待 Phase 5 用户提供证书后处理。

---

## 待确认

- 是否授权清理 `_tmp_home/`（测试 sandbox HOME，非用户数据）等临时产物？
- pyinstaller 版本是否由你在构建机核对后告知，我据实写入 `requirements.txt`？（或我先写入保守推荐值并标注待核对）
