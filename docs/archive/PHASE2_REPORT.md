# Desktop Cleaner Phase 2 Report

> 阶段目标：仅修复 P0 高风险问题（文件安全 + 数据一致性）。
> 原则：最小修改 · 复用 `operations.status`（未新增字段）· 不重写 core 业务规则 · 不修改产品流程 · 不增加功能。

## 1. 修改文件

| 文件 | 改动类型 | 说明 |
|---|---|---|
| `src/core/organizer.py` | 修改 | 新增 `move_items()`（移动 + 逐文件校验）；`organize()` 复用之；`undo_plan()` 还原目标改用 `_unique_target()`（P0-3）；`execute_undo()` 复用 `move_items()`；`OrganizeResult` 增加 `failed_items` 字段 |
| `src/core/__init__.py` | 修改 | 导出 `move_items` |
| `src/data/operation_repo.py` | 修改 | 新增 `bulk_insert_pending()`（P0-1，落库 pending）、`update_statuses_by_target()`（P0-1，结算 moved/failed）、`apply_undo_result()`（P0-2，仅成功还原的置 undone 并返回失败清单）、`reconcile_pending()`（P0-1 启动恢复，只校准状态不移动文件） |
| `src/data/database.py` | 修改 | 新增 `data_dir()`，暴露应用数据目录供 scanner 做安全护栏 |
| `src/core/scanner.py` | 修改 | 跳过 `desktop.ini` / `thumbs.db` / `ehthumbs.db` 与隐藏文件（P0-4）；扫描到应用自身数据目录时抛 `ValueError`（P0-4）；`data_dir` 改为函数内惰性导入以打破循环依赖 |
| `src/ui/pages/organize_page.py` | 修改 | `_task_organize` 改为「先 `bulk_insert_pending` → 再 `move_items` → 再 `update_statuses_by_target`」；撤销完成页在部分失败时给出明确提示（P0-2 可见化，非 UI 重构） |
| `src/ui/undo.py` | 修改 | `run_undo` 改用 `apply_undo_result`：全部成功才标记 history=`undone`，部分失败保留 `moved` 并返回 `failed_files` |
| `main.py` | 修改 | 启动时调用 `operation_repo.reconcile_pending()`（P0-1 恢复） |
| `tests/test_security.py` | 新增 | P0 四项专项测试（见第 3 节） |

## 2. P0 修复结果

| 问题 | 结果 | 修复要点 |
|---|---|---|
| P0-1 整理中断导致无法撤销 | ✅ PASS | 移动前先落库 `pending`；新增 `reconcile_pending()` 启动恢复（仅 stat 校准：`target` 存在且 `source` 消失 → `moved`，否则 → `failed`），不自动移动任何文件。中断后移动仍可撤销 |
| P0-2 撤销失败仍标记成功 | ✅ PASS | 抽出 `apply_undo_result()`：仅被成功还原的 op 置 `undone`；失败的保留 `moved` 并返回失败清单；history 仅全成功时置 `undone` |
| P0-3 撤销路径碰撞保护 | ✅ PASS | `undo_plan()` 还原目标复用 `_unique_target()`，原位置已有同名文件时自动 `xxx (1)`，**禁止覆盖**（与整理端对称） |
| P0-4 系统文件 / 应用目录保护 | ✅ PASS | scanner 跳过 `desktop.ini`/`thumbs.db`/`ehthumbs.db` 与隐藏文件；扫描到应用自身数据目录（`%APPDATA%/DesktopCleaner` 或 `DESKTOP_CLEANER_HOME`）抛明确 `ValueError` |

## 3. 测试结果

```text
$ PYTHONPATH=src python tests/test_core.py
[1]~[7] scan / organize / 持久化 / 重扫不重复 / undo / 碰撞重命名 / 日期模式
ALL TESTS PASSED

$ PYTHONPATH=src python tests/test_security.py
[P0-1] 整理中断恢复 (pending + reconcile)        ok x5
[P0-2] 部分撤销失败不误标记                    ok x6
[P0-3] 撤销碰撞保护（不覆盖）                   ok x4
[P0-4] 扫描保护（系统/隐藏/应用目录）           ok x7  (含隐藏文件，Windows ctypes 生效)
ALL P0 SECURITY TESTS PASSED
```

验证手段：
- `tests/test_core.py`：**原有全量逻辑测试，零回归**（确认 P0 修改未破坏扫描→整理→持久化→撤销链路）。
- `tests/test_security.py`：**新增 4 组 P0 测试**，覆盖中断恢复、部分 undo、undo 碰撞、扫描保护。
- `python -m compileall src main.py`：**全部源码字节码编译通过**（含 PySide6 UI 模块，语法无误）。

> 说明：本环境为无 PySide6 的受管 Python，UI 模块仅做编译校验；GUI 冒烟（离屏截图）放到 Phase 5 发布验证。

## 4. 风险说明

- **已有用户数据**：无影响。`reconcile_pending()` 对正常完成的记录（无 `pending`、无 `running`）为**空操作**；不会改动已 `done` 的历史与操作。
- **已有数据库**：无影响。完全复用既有 `operations.status`（`pending`/`moved`/`failed`/`undone`）与 `history.status`，**未新增任何字段、未改表结构**，旧库向后兼容。
- **已有 EXE**：未重建（Phase 5 才打包）。源代码与既有 `build.spec` 兼容；新增逻辑均为标准库 + 已有依赖，无新增打包项（注意 `ui.undo` 已纳入 `hiddenimports`，本阶段未改动 spec）。
- **循环依赖**：scanner 对 `data.database` 的导入改为函数内惰性导入，避免 `core→data→core` 启动期循环 import。
- **文件安全**：所有路径保持「只移动、不删除、碰撞重命名不覆盖」；`move_items` 增加移动后校验，失败即记为 `failed` 而非误标成功。

## 5. 下一阶段建议

✅ **可以进入 Phase 3（P1）**。

建议 Phase 3 优先处理（均非阻断，属稳定性/架构/异常增强）：
- P1-a SQLite 开启 `WAL` + `busy_timeout`；撤销逐条开连接改为批量。
- P1-b 跨模式递归重复整理去重（`scanner` exclude 仅含当前模式产物）。
- P1-c 失败原因明细 + `logger` 实际落盘（当前 `except` 仅进内存）。
- P1-d Windows 长路径（`\\\\?\\` 前缀）/ OneDrive / 权限不足的统一异常上报。
- P1-e `Worker` 异常统一上抛与用户提示收敛。

> 备注：本次严格未触碰 P1/P2 与 UI 重构，符合 Phase 2 范围约束。
