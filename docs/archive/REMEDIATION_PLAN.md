# Desktop Cleaner — 修复实施计划（Phase 1：Audit 问题确认）

> 本文件为**第一阶段交付物**：仅确认问题、整理修复清单与影响范围，**未修改任何代码**。
> 依据：`AUDIT_REPORT.md`（已同步修正，原文件曾被覆盖为提示词文本）。
> 原则：最小修改 · 文件安全优先 · 保持「扫描→预览→整理→撤销」完整可用 · 不动 `core` 业务规则与既有用户路径规则。

---

## 一、修复清单总览（问题编号 → 风险 → 影响文件 → 修复方案 → 预计风险）

### P0 — 必须修复（安全 / 数据一致性 / 文件损失）

| 编号 | 问题 | 风险等级 | 涉及文件 | 最小修复方案 | 预计风险 |
|---|---|---|---|---|---|
| **P0-1** | 中断整理 → 移动不可撤销（记录时机在移动之后） | 高 | `src/ui/pages/organize_page.py`(`_task_organize`)、`src/data/operation_repo.py`、`src/ui/app_shell.py`/`main.py` | 移动**前**用新增 `bulk_insert_pending(hid, items)` 落库（status=`pending`，复用现有 `operations.status` 列）；`organize()` 后按 `OrganizeResult` 把各 op 改为 `moved`/`failed`；启动时 `reconcile_pending()` 通过 stat 源/目标路径校准残留 `pending`（**只读不移动**）。 | 低。列已存在；reconcile 仅校准 DB |
| **P0-2** | 撤销部分失败仍标记 `undone` | 高 | `src/ui/undo.py`(`run_undo`)、`src/ui/pages/{history,dashboard,organize}_page.py` | `run_undo` 仅当 `result.failed==0` 才置 history 为 `undone`；有失败则保持 `done` 并回传失败清单，由页面弹窗列出。 | 低。仅改状态判定与提示 |
| **P0-3** | 撤销端无碰撞重命名（原位置同名 → FileExistsError 被吞） | 高 | `src/core/organizer.py`(`execute_undo`) | 复用 `_unique_target()` 计算原位置唯一路径，与整理端对称，避免覆盖/抛错。 | 极低。仅改目标文件名，不删不覆盖 |
| **P0-4** | 系统/隐藏文件无防护 + 未拒绝整理自身数据目录 | 高 | `src/core/scanner.py`、`src/ui/pages/organize_page.py` | (a) scanner 跳过 `desktop.ini`/`thumbs.db`/`.lnk`/Windows 隐藏属性文件；(b) 扫描前校验根目录 ≠ 且 ∉ 应用数据目录（`_app_base()/data`），否则拒绝并提示。 | 低。保守跳过系统垃圾；小概率误伤用户同名隐藏文件（UI 注明） |

### P1 — 重要优化（架构 / 异常 / 性能 / 发布）

| 编号 | 问题 | 风险等级 | 涉及文件 | 最小修复方案 | 预计风险 |
|---|---|---|---|---|---|
| **P1-1** | SQLite 无 WAL/busy_timeout；撤销逐条开连接 | 中 | `src/data/database.py`、`src/data/operation_repo.py`、`src/ui/undo.py` | `get_connection()` 增 `PRAGMA journal_mode=WAL; busy_timeout=5000; synchronous=NORMAL`（向后兼容）；新增 `update_statuses(hid, status)` 单连接批量更新。 | 低。WAL 旧库自动升级；注意程序退出 checkpoint |
| **P1-2** | 跨模式递归重复整理 | 中 | `src/core/scanner.py`、`src/core/rules.py` | `exclude_dirs` 改为**始终排除「分类名 ∪ 日期目录」并集**，与 mode 无关。 | 中低。用户同名普通文件夹（如 `Images`）会被跳过，UI 预览注明 |
| **P1-3** | 失败原因只显示计数；logger 闲置 | 中 | `src/core/organizer.py`、`src/core/scanner.py`、`src/utils/logger.py`、完成页 | `core` 接入 logger 记录每次移动成功/失败（路径+原因）；完成页增加「查看失败明细」入口（读 `OrganizeResult.errors`）。 | 低 |
| **P1-4** | exe 无代码签名（发布阻断） | 中 | `build.bat`、发布说明 | 非纯代码：在 `build.bat` 增加 `signtool sign` 占位步骤；文档说明需 EV/自签证书消除 SmartScreen。 | 需外部证书；不阻塞代码，阻塞「可放心发布」 |
| **P1-5** | Windows 长路径/中文/空格兼容加固 | 中 | `src/core/organizer.py` | 移动前对 >260 字符路径在 Windows 加 `\\?\` 前缀；规范路径处理，兼容 OneDrive 重解析点。 | 低 |
| **P1-6** | UI 异常未提示 / Worker 错误未上抛 | 中 | `src/ui/state/worker.py`、各 page | 复核 Worker 异常信号；缺失则增 `error` 信号并在页面 toast/弹窗，避免静默失败。 | 低 |

### P2 — 体验优化（日志 / 提示 / 整理 / 发布卫生）

| 编号 | 问题 | 风险等级 | 涉及文件 | 最小修复方案 | 预计风险 |
|---|---|---|---|---|---|
| **P2-1** | 日志系统增强 | 低 | `src/utils/logger.py` | 结构化 `logs/`：`时间/级别/模块/消息`，覆盖启动/扫描/整理/撤销/异常（P1-3 已接入 core）。 | 低 |
| **P2-2** | 测试补充 | 低 | `tests/` | 新增 `test_safety.py`(移动成功/失败/恢复)、`test_exception.py`(权限/不存在)、`test_consistency.py`(中断)、`test_win_paths.py`(中文/空格/长路径)。 | 低 |
| **P2-3** | 仓库卫生 | 低 | 工作树、`.gitignore` | 清理 `_*.txt`/`_tmp_home/`/`dist_old_*`；`.gitignore` 增补。 | 低 |
| **P2-4** | 构建可复现 | 低 | `requirements.txt`、`build.bat` | 锁定版本（`PySide6==x.y.z` 等）；`build.bat` 对齐 `build.spec` 的 `hiddenimports`。 | 低 |
| **P2-5** | 技术债 shim 收敛 | 低 | `src/ui/theme_manager.py`、`src/ui/themes.py` | 后续可选：去掉转发 shim，统一到 `ui/theme/`。 | 低 |

---

## 二、分阶段路线图（与审计第 5 节对齐）

| 阶段 | 范围 | 退出标准 |
|---|---|---|
| **Phase 1（本阶段）** | 确认问题、产出清单 | 已交付，**等待确认**，未改代码 |
| **Phase 2（P0）** | P0-1~P0-4 | 4 项闭环；`test_core` 仍 PASS；EXE 启动无回归 |
| **Phase 3（P1）** | P1-1~P1-6 | 架构/异常/性能/Win 兼容/UI 稳定；签名步骤就位（证书待用户提供） |
| **Phase 4（P2）** | P2-1~P2-5 | 日志、测试、仓库与构建卫生完成 |
| **Phase 5（发布验证）** | 端到端 | 测试 → PyInstaller 构建 → EXE 启动 → 真实目录验证 |

---

## 三、每阶段交付格式（后续阶段按此回填）

```
Desktop Cleaner Remediation Report
Phase:        <阶段>
修改文件:      <文件列表>
修复问题:      <P0-x / P1-x / P2-x>
修改说明:      <最小修改点>
测试:          <跑了哪些测试 / 结果>
风险:          <遗留风险>
下一步:        <下一阶段或待确认项>
```

---

## 四、当前状态与下一步

- ✅ 已读取并**修正** `AUDIT_REPORT.md`（原文件被覆盖为提示词，现已恢复真实审计内容）。
- ✅ 已产出本计划，覆盖全部 P0/P1/P2 问题与最小修复路径、影响文件、预计风险。
- ⛔ **未修改任何代码**（Phase 1 硬性约束）。
- ⏳ **等待你确认**是否进入 **Phase 2（P0 修复）**。确认后我将按上述 P0-1~P0-4 方案实施，并回填 Phase 2 报告。

> 提示：P0-1 的 `reconcile_pending()` 与 P0-4 的自保护校验是「文件安全优先」的关键护栏，建议优先在 Phase 2 落地；P1-4 代码签名需你提供证书，可先放占位步骤。
