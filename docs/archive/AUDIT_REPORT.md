# Desktop Cleaner — Production Readiness & Security Audit Report

> 审计阶段：第一阶段（仅分析，未修改任何代码）
> 审计对象：`desktop-cleaner/`（Windows PySide6 桌面文件整理助手）
> 审计维度：架构质量 / 安全能力 / 稳定性与数据一致性 / 发布就绪 / 测试
> 证据：实际通读全部 `src/**/*.py` + `build.*` + `requirements.txt` + `.gitignore`；`tests/test_core.py` 用受管 Python 3.13 实跑 **ALL PASSED**。

---

## 0. 总判定

**暂不可发布，但核心安全底座扎实。** 文件「只移动不删除 + 预览门控 + 冲突重命名」严格落实，分层清晰、core 零 Qt 依赖。阻断项集中在**数据一致性（中断/撤销）**与**发布交付物**两块，均可在不重写业务规则的前提下修复。

---

## A. 架构质量

| 项 | 结论 | 说明 |
|---|---|---|
| 分层 | ✅ 良好 | `core/`（零 Qt）、`data/`、`ui/` 边界清晰，业务层冻结纪律良好 |
| 迁移残留 | ⚠️ P2 | `ui/theme_manager.py`、`ui/themes.py` 为 shim 转发到 `ui/theme/`，属中途迁移脚手架，无功能影响 |
| `init_db()` 双调用 | ⚠️ P2 | `app_shell.py` 与 `main.py` 均可能触发；`CREATE TABLE IF NOT EXISTS` 幂等，无破坏，但属冗余 |
| `custom_page.py` | ⚠️ 待确认 | 功能不完整，未接入主流程，不建议本次改动 |

---

## B. 安全能力

| 项 | 结论 | 说明 |
|---|---|---|
| 只移动不删除 | ✅ 通过 | `organizer.organize/execute_undo` 全程 `shutil.move`，无 `os.remove`/`shutil.rmtree`（除 `_remove_empty_category_dirs` 仅清理空目录） |
| 预览门控 | ✅ 通过 | `preview_report.py`「开始整理」显式确认 + 「不会删除」文案，契约完整 |
| 冲突重命名 | ✅ 通过 | `organizer._unique_target()` 碰撞时 `name (1).ext`，**整理端**不覆盖 |
| 系统/隐藏文件防护 | ❌ P0 | `scanner.py` 不过滤 `desktop.ini`/`thumbs.db`/`.lnk`/隐藏属性文件；可能搬运系统文件 |
| 自保护 | ❌ P0 | 未拒绝「整理应用自身数据目录」（`_app_base()/data`），一旦选中会搬运自己的 SQLite/日志，程序损坏 |

---

## C. 稳定性与数据一致性（核心缺陷区）

### C.1 ❌ P0 — 中断整理 → 移动不可撤销
`organize()` 先把**所有文件移动完毕**，页面再 `bulk_insert` 写入 `operations`。
若进程被强杀 / 关窗 / 断电发生在「移动后、入库前」，**文件已移走但 `operations` 为空** → 这批移动永远无法撤销，击穿「每次整理可还原」的核心承诺。
> 注：经复核，`operations.status` 列**已存在**（`moved`/`undone`），故本项非「缺列」，而是**记录时机**问题——应在移动前/移动中落库。

### C.2 ❌ P0 — 撤销部分失败仍标记 `undone`
`ui/undo.run_undo()` 先 `execute_undo()`，再逐 op 更新状态，**最后无条件** `history_repo.update_status(hid,"undone")`。
一旦个别文件还原失败（见 C.3），history 仍被标 `undone`，用户误以为全部还原，且因状态已非 `done` 无法再次撤销 → 真实部分还原 + 数据库谎报完成。

### C.3 ❌ P0 — 撤销端无碰撞重命名
`execute_undo()` 直接用 `shutil.move(src, original_path)`，若原位置已有同名文件（用户曾重新放入 / 部分状态残留），抛 `FileExistsError` 被 `except` 吞掉 → 源文件留在分类目录、history 却标记 `undone`，与整理端行为不对称。

### C.4 ⚠️ P1 — 跨模式递归重复整理
`scanner.scan()` 的 `exclude_dirs` 仅按**当前模式**产出目录过滤（`type`→分类名，`date`→日期目录）。
先「按类型」生成 `Images/`，再「按日期+递归」扫描时，`Images/` 不被排除 → 已分类文件被二次搬运。

### C.5 ⚠️ P1 — SQLite 无 WAL / busy_timeout；撤销逐条开连接
`database.get_connection()` 仅开 `foreign_keys`，无 `journal_mode=WAL`、`busy_timeout`。
大批量撤销时 `run_undo` 对每个 op 调 `operation_repo.update_status()` 各自开一条连接，慢且有锁风险。

### C.6 ⚠️ P1 — 失败原因只显示计数，logger 闲置
`OrganizeResult.errors` 已收集明细，但 UI 仅展示计数；`utils/logger.py` 已建却未在 `core` 中使用，用户无法诊断「为何某文件失败」。

---

## D. 发布就绪

| 项 | 结论 | 说明 |
|---|---|---|
| exe 代码签名 | ❌ P1（发布阻断） | `build.spec` `codesign_identity=None` → SmartScreen「未知发布者」+ 杀软误报。需外部证书，非纯代码可解 |
| 仓库卫生 | ⚠️ P2 | 工作树含 `_*.txt`、`_tmp_home/`（含真实 DB）、`dist_old_*`；`.gitignore` 未覆盖 |
| 构建可复现 | ⚠️ P2 | `requirements.txt` 未锁版本；`build.bat` 缺 `build.spec` 的 `hiddenimports`，两条打包路径结果可能不一致 |

---

## E. 测试

- ✅ `tests/test_core.py` 实跑通过（扫描/整理/持久化/幂等/撤销/碰撞/日期模式）。
- ⚠️ `tests/test_appshell.py` 依赖 GUI，当前 venv 无 PySide6，未能在本环境实跑。
- ❌ P2 缺口：缺**文件安全（移动成功/失败/恢复）**、**异常（权限/不存在）**、**数据一致性（中断）**、**Windows 路径（中文/空格/长路径）**专项测试。

---

## 3. 问题分级汇总（映射到修复计划）

### P0（安全 / 数据一致性 / 文件损失风险 — 必须修）
- **P0-1** C.1 中断整理 → 移动不可撤销（记录时机）
- **P0-2** C.2 撤销部分失败仍标记 `undone`
- **P0-3** C.3 撤销端无碰撞重命名
- **P0-4** B.3 系统/隐藏文件无防护 + 未拒绝整理自身数据目录

### P1（架构 / 异常处理 / 性能 / 发布）
- **P1-1** C.5 SQLite 无 WAL/busy_timeout + 撤销逐条开连接
- **P1-2** C.4 跨模式递归重复整理
- **P1-3** C.6 失败原因只显示计数 + logger 闲置
- **P1-4** D.1 exe 无代码签名（需外部证书）
- **P1-5** F Windows 长路径/中文/空格兼容加固
- **P1-6** G UI 异常未提示 / Worker 错误上抛

### P2（日志 / 提示 / 代码整理 / 发布卫生）
- **P2-1** D 日志系统增强（结构化 logs/）
- **P2-2** H 测试补充（安全/异常/一致性/Win 路径）
- **P2-3** D.2 仓库卫生（清理临时产物 + .gitignore）
- **P2-4** D.3 构建可复现（锁版本 + 对齐 build.bat）
- **P2-5** 技术债 shim 收敛（低优先级，可放后续）

---

## 4. 已验证正面项（修复时务必保持）
1. 分层清晰、`core/` 零 Qt 依赖、业务层冻结纪律良好。
2. 「扫描→预览→整理→撤销」完整链路可用；预览门控与「不会删除」承诺落实。
3. 整理端冲突重命名正确；`operations.status` 状态机已存在。
4. `test_core.py` 实跑 ALL PASSED，是可回归的硬证据。

---

## 5. 路线图（与修复计划 Phase 2-5 对齐）
- **阶段 2（P0）**：闭环 4 项 P0，跑全测试。
- **阶段 3（P1）**：架构/异常/性能/Windows 兼容/UI 稳定 + 签名说明。
- **阶段 4（P2）**：日志、测试补充、仓库与构建卫生。
- **阶段 5（发布验证）**：测试 → PyInstaller 构建 → EXE 启动 → 真实目录验证。
