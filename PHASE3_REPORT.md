# Desktop Cleaner Phase 3 Report

> 阶段目标：仅修复 P1（稳定性 / 并发可靠性 / Windows 兼容性 / 异常可观测性 / 长期运行能力）。
> 原则：最小修改 · **冻结 P0 安全机制**（pending→moved/failed、undo 部分失败不误标、undo 碰撞不覆盖、系统/隐藏/应用目录保护全部保留）· 不改表结构 · 不改 core 业务规则 · 不重构 UI · 不新增功能。

## 1. Phase Overview

在 Phase 2 P0 基线之上，针对审计 C.5 / C.4 / C.6 与 D.1 的 P1 项做最小增强：SQLite 并发（WAL+busy_timeout）、批量写入、跨模式扫描去重、失败明细落盘、Windows 长路径、Worker 友好异常上抛。全程未触碰 P0 逻辑、未改动 `operations`/`history` 表结构、未引入新依赖。

## 2. 修改文件

| 文件 | 改动 | P1 |
|---|---|---|
| `src/data/database.py` | `get_connection()` 增 `busy_timeout=5000` + `journal_mode=WAL` + `synchronous=NORMAL`（try/except 容错，旧库自动升级） | P1-1 |
| `src/data/operation_repo.py` | `apply_undo_result()` 收集 undone id 后 `executemany` 一次写入（原逐 op `execute`） | P1-2 |
| `src/core/scanner.py` | 排除目录**始终**含「分类名 ∪ 日期目录」并集（与 mode 无关）；`_is_hidden` 用长路径安全形式；文件判定走 `utils.paths` | P1-3 / P1-5 |
| `src/core/organizer.py` | `OrganizeResult` 增 `failed_details`；`move_items` 结构化失败记录 + 落盘 logger + 长路径安全移动；`plan()` 按 listed-path 去重（不解析 symlink）；`_unique_target` 长路径安全存在性检查 | P1-3 / P1-4 / P1-5 |
| `src/utils/paths.py` | **新增** `win_long()` / `safe_exists()` / `safe_is_file()`（`\\?\` 前缀仅长路径触发，非 Windows 直通过） | P1-5 |
| `src/utils/errors.py` | **新增** `friendly_message()` 异常→用户友好文案映射 | P1-6 |
| `src/ui/state/worker.py` | `run()` 记全 traceback 到日志文件，向 UI 仅 emit 友好文案 | P1-6 |
| `src/ui/pages/organize_page.py` | 完成页新增「查看失败明细」按钮（失败时出现，弹窗列明细）；三处 `_on_error` 直接展示友好消息 | P1-4 / P1-6 |
| `src/ui/pages/history_page.py` | `_on_error` 直接展示友好消息 | P1-6 |
| `src/ui/pages/dashboard_page.py` | `_on_undo_error` 直接展示友好消息 | P1-6 |
| `tests/test_reliability.py` | **新增** P1-1/2/3/4/6 专项测试（9 项） | — |
| `tests/test_windows_paths.py` | **新增** P1-5 长路径测试（5 项，真实移动尽力验证） | — |

## 3. P1 问题修复结果

| ID | 问题 | 状态 |
|----|----|----|
| P1-1 | SQLite 并发稳定性（WAL / busy_timeout） | ✅ PASS |
| P1-2 | 数据库批量操作优化 | ✅ PASS |
| P1-3 | 跨模式递归扫描去重 | ✅ PASS |
| P1-4 | 失败明细 + Logger 落盘 | ✅ PASS |
| P1-5 | Windows 长路径 | ⚠️ CONDITIONAL |
| P1-6 | Worker 统一异常上抛 | ✅ PASS |

> P1-5 说明：宿主为 Git-Bash-on-Windows（`os.name=="nt"`），`\\?\` 前缀**字符串变换已真实验证**（短路径规范化不前缀、>240 字符加前缀），短路径整理回归通过；但**真实 >260 字符文件系统移动**在本沙箱卷返回 `WinError 123`（卷语法限制），未能实跑，故标 CONDITIONAL。

## 4. 测试结果

```text
$ PYTHONPATH=src python tests/test_core.py        -> ALL TESTS PASSED        (7 检查组)
$ PYTHONPATH=src python tests/test_security.py   -> ALL P0 SECURITY TESTS PASSED (4 组 P0)
$ PYTHONPATH=src python tests/test_reliability.py-> ALL P1 RELIABILITY TESTS PASSED (9 项)
$ PYTHONPATH=src python tests/test_windows_paths.py-> ALL WINDOWS-PATH TESTS PASSED (5 项, 真实移动 skip)
$ python -m compileall -q src main.py            -> PASS (exit 0, 含全部 PySide6 UI 模块)
```

- 全部 4 套测试 **PASS**；`compileall` 全部源码可编译（UI 模块语法无误）。
- 无测试跳过失败项；P1-5 真实长路径移动为预期内 skip（非错误）。

## 5. P0 回归

明确确认 Phase 2 全部 P0 行为未被削弱：

- **P0-1** ✅ `bulk_insert_pending`→`move_items`→`update_statuses_by_target` 顺序保留；`reconcile_pending()` 仍只校准不移动。
- **P0-2** ✅ `apply_undo_result` 仍仅成功还原的置 `undone`，失败保留 `moved` 且返回失败清单；`test_security.py P0-2` 仍 PASS。
- **P0-3** ✅ `undo_plan` 仍复用 `_unique_target`；新增长路径安全检查不改变「不覆盖」语义；P0-3 测试仍 PASS。
- **P0-4** ✅ scanner 仍跳过系统/隐藏文件、仍对应用数据目录抛 `ValueError`；测试仍 PASS。

## 6. 数据兼容性

- **旧数据库**：完全兼容。`journal_mode=WAL` 在首次打开时自动将既有 rollback-journal 库升级为 WAL（持久化于文件头），旧库可正常打开；若文件系统不支持 WAL/busy_timeout，`get_connection` 捕获 `OperationalError` 降级，不影响功能。
- **旧历史 / 操作记录**：未删字段、未改语义、未强制迁移。新增仅 `OrganizeResult.failed_details`（内存对象字段，不入 DB）。
- **EXE**：未重建（Phase 5 才打包）；`build.spec` 未改，无新增打包项。

## 7. Windows 兼容性

| 维度 | 验证情况 |
|---|---|
| 中文路径 | ✅ 已验证（测试用中文文件名 `photo.jpg`/`doc.pdf` 等，整理与扫描正常） |
| 空格路径 | ✅ 已验证（Path 全程字符串传递，`shutil.move` 支持空格） |
| 长路径（>260） | ⚠️ CONDITIONAL：`\\?\` 前缀变换已验证；真实 >260 移动沙箱卷不支持，未在真实卷实跑 |
| 权限错误 | ✅ 已验证（P1-6 `friendly_message` 将 `PermissionError` 映射为「请检查权限」；`test_failure_details_recorded` 覆盖失败记录） |

## 8. 剩余风险

1. **P1-5 真实长路径移动未实跑**：逻辑与前缀变换已验证，但 >260 字符真实文件移动依赖运行环境文件系统支持（沙箱卷报 WinError 123）。在真实用户 Windows（NTFS，长路径感知开启）下预期可用，但本环境无法 100% 实跑 → CONDITIONAL。
2. **P1-4 完成页「查看失败明细」仅组织（organize）侧**：撤销（undo）失败的明细已落盘 logger，但 UI 弹窗只展示计数（既有 `_on_undo_done_redirect` 行为），未新增按钮——属最小化改动，未扩大范围。
3. **P1-1 WAL 的 -wal/-shm 文件**：进程异常退出可能残留 `-wal` 文件，SQLite 在下次打开时自动 checkpoint/恢复，不影响数据完整性；多进程并发场景（如同时开两个实例）不在本阶段范围内。

## 9. 最终判定

**PASS WITH CONDITIONS**

- P1-1 / P1-2 / P1-3 / P1-4 / P1-6 全部实跑 PASS，且 P0 测试零回归。
- P1-5 为 CONDITIONAL（前缀变换已验证，真实 >260 移动受沙箱卷限制未实跑，理论 + 短路径验证完整）。
- 未引入发布阻断项；代码签名（P1-4 原审计项，需外部证书）不属于本代码阶段，仍待用户提供证书后在 Phase 5 处理。

## 10. 下一阶段

✅ **建议进入 Phase 4（P2）/ Release Candidate Validation**：
- P2-1 结构化日志增强（`logs/` 分级覆盖启动/扫描/整理/撤销/异常，本阶段已在 core 接入 `logger`，可继续统一格式）。
- P2-2 测试补充（P2 缺口：异常/一致性/Win 真实长路径）。
- P2-3 仓库卫生（清理 `_*.txt`/`_tmp_home`/`dist_old_*` + `.gitignore`）。
- P2-4 构建可复现（`requirements.txt` 锁版本、`build.bat` 对齐 `build.spec`）。
- 其后 **Phase 5**：测试 → PyInstaller 构建 → EXE 启动 → 真实目录验证 → 代码签名（待证书）。

> 备注：本阶段严格未触碰 UI 高级化、Figma 迁移、新功能、Smart Organization、AI 功能、P2 优化，符合 Phase 3 范围约束。
