# Desktop Cleaner Phase 4 Report

> 阶段目标：闭环剩余 P2（日志增强 / 测试补充 / 仓库与构建卫生），建立 Phase 5 RC 的可重复、可验证发布基线。
> 原则：最小修改 · **冻结 P0 安全机制**（pending→moved/failed、undo 部分失败不误标、undo 碰撞不覆盖、系统/隐藏/应用目录保护全部保留）· 不改表结构 · 不改 core 业务规则（分类/路径/撤销语义）· 不重构 UI · 不新增功能。

## 1. Phase Overview

在 Phase 2（P0）/ Phase 3（P1）基线之上，针对审计 D / H 段的 P2 项做收口：结构化日志格式补全 + 生命周期日志、补齐测试缺口、真实验证 Windows 长路径（并修复发现的产品缺陷）、清理仓库临时/旧构建产物并补全 `.gitignore`、锁依赖版本并统一 build 脚本、确认 shim 保留。全程未触碰 P0/P1 逻辑、未改 DB 表结构、未引入新依赖。

> 重要发现：P2-3 真实实验中暴露出 P1-5 长路径支持的一个**真实缺口**——`move_items` 创建目标父目录时未使用 `win_long` 前缀，导致 >260 字符深路径移动在 `mkdir` 阶段即失败（`WinError 3`）。已做**最小单行修复**补全，重跑后 346 字符深路径的 `move` 与 `undo` 均**真实通过**。

## 2. 修改文件

| 文件 | 改动 | P2 |
|---|---|---|
| `src/utils/logger.py` | formatter 增加 `%(name)s`（module 字段），保持「时间 [级别] 模块 消息」机器+人工可读 | P2-1 |
| `src/core/scanner.py` | 导入 logger；`scan` 入口/出口写 INFO（root/mode/recursive/文件数/字节） | P2-1 |
| `src/core/organizer.py` | `move_items` 末尾补一行整理汇总 INFO；目标父目录创建改用 `os.makedirs(win_long(item.target.parent))`（P1-5 长路径补全） | P2-1 / P2-3 |
| `src/ui/undo.py` | 导入 logger；`run_undo` 写 undo 开始/完成(或 PARTIAL) INFO | P2-1 |
| `main.py` | 启动写 `APP START`、reconcile 结果 `APP RECOVERED` INFO | P2-1 |
| `tests/test_p2_coverage.py` | **新增** 4 组 P2 场景（源缺失 / 旧库WAL升级 / running→done reconcile / 日志格式） | P2-2 |
| `requirements.txt` | `PySide6>=6.7.0` → `PySide6==6.7.0`；新增 `pyinstaller==6.11.1`（标注 CANDIDATE / PENDING VERIFICATION） | P2-5 |
| `build.bat` | 改为调用 `pyinstaller build.spec`（单一事实源）；从 `requirements.txt` 安装；可选条件签名占位（无证书跳过） | P2-6 |
| `.gitignore` | 增补 `_tmp_home/`、`_*.txt`、`.pytest_cache/`、`*.db-wal`、`*.db-shm`、`build_old_*/`、`dist_old_*/` | P2-4 |
| 工作树 | 删除 `_*.txt`×6、`dist_old_*`×5、`build_old_*`×1、各 `__pycache__`（字节码可重建） | P2-4 |
| `src/ui/theme_manager.py`、`src/ui/themes.py` | **未改动**（shim 仍被 15+ 模块引用，保留并记录） | P2-7 |

## 3. P2 修复结果

| ID | 问题 | 状态 |
|----|----|----|
| P2-1 | 结构化日志增强 | ✅ PASS |
| P2-2 | 测试覆盖增强 | ✅ PASS |
| P2-3 | Windows 长路径真实验证 | ✅ PASS（含一处产品缺陷修复；见 §8 备注） |
| P2-4 | 仓库卫生 | ✅ PASS |
| P2-5 | 构建可复现 | ⚠️ CONDITIONAL |
| P2-6 | 构建一致性 | ✅ PASS |
| P2-7 | shim 收敛 | 🔒 NO ACTION（保留） |

> P2-5 说明：本环境**未安装 PyInstaller**，真实构建工具版本**未在此验证**。需求文件已写入候选版本并明确标注 `CANDIDATE / PENDING VERIFICATION`，待 Phase 5 在真实构建机核对。故 P2-5 维持 **CONDITIONAL**（非伪造 PASS）。

## 4. 测试结果

```text
$ PYTHONPATH=src python tests/test_core.py        -> ALL TESTS PASSED          (7 组, P0/P1 零回归)
$ PYTHONPATH=src python tests/test_security.py   -> ALL P0 SECURITY TESTS PASSED (4 组 P0)
$ PYTHONPATH=src python tests/test_reliability.py-> ALL P1 RELIABILITY TESTS PASSED (9 项)
$ PYTHONPATH=src python tests/test_windows_paths.py-> ALL WINDOWS-PATH TESTS PASSED (5 项)
$ PYTHONPATH=src python tests/test_p2_coverage.py-> ALL P2 COVERAGE TESTS PASSED (4 组, 新增)
$ python -m compileall -q src main.py            -> PASS (exit 0, 含全部 PySide6 UI 模块)
```

- 测试数量：既有 4 套 + 新增 `test_p2_coverage.py`（4 组）共 **25 项断言级场景**，全部 PASS；0 FAIL / 0 人为 skip。
- `compileall` 退出码 0：全部源码（含 PySide6 UI 模块）语法/字节码编译通过。

## 5. P0 回归

明确确认 Phase 2 全部 P0 行为未被削弱：
- **P0-1** ✅ `bulk_insert_pending`→`move_items`→`update_statuses_by_target` 顺序保留；`reconcile_pending()` 仍只校准不移动；`test_security P0-1` 仍 PASS。
- **P0-2** ✅ `apply_undo_result` 仍仅成功还原的置 `undone`，失败保留 `moved` 并返回失败清单；`test_security P0-2` 仍 PASS。
- **P0-3** ✅ `undo_plan` 仍复用 `_unique_target` 不覆盖；新增 `win_long` 父目录创建不改变「不覆盖」语义；`test_security P0-3` 仍 PASS。
- **P0-4** ✅ scanner 仍跳过系统/隐藏文件、仍对应用数据目录抛 `ValueError`；`test_security P0-4` 仍 PASS。

## 6. P1 回归

- **P1-1** ✅ WAL/busy_timeout（`test_reliability` 通过）。
- **P1-2** ✅ 批量写入（`test_reliability` 通过）。
- **P1-3** ✅ 跨模式去重（`test_reliability` 通过）。
- **P1-4** ✅ 失败明细+日志（`test_reliability` + 新增 `test_p2_coverage T1` 通过）。
- **P1-5** ✅ 长路径：`\\?\` 前缀变换 + **本次补全的目标父目录 `win_long` 创建**，已在 346 字符深路径真实通过（见 §8）。
- **P1-6** ✅ Worker 友好异常（`test_reliability` 通过）。

## 7. 数据兼容性

- **旧数据库**：完全兼容。`journal_mode=WAL` 首次打开自动将 rollback-journal 库升级（新增 `test_p2_coverage T2` 真实验证：旧式库经 `get_connection` 打开后表/索引可用、可读写）。
- **旧历史 / 操作记录**：未删字段、未改语义、未强制迁移。本次仅新增内存对象字段（`failed_details`，不入 DB）与日志。
- **WAL 运行时文件**（`*.db-wal`/`*.db-shm`）：属 SQLite 正常运行产物，已加入 `.gitignore` 忽略，不视为垃圾、不删除。
- **EXE**：未重建（Phase 5 才打包）。

## 8. Windows 兼容性（P2-3 真实证据）

| 维度 | 验证情况 |
|---|---|
| 中文路径 | ✅ 已验证（测试用中文文件名） |
| 空格路径 | ✅ 已验证（Path 全程字符串传递） |
| 长路径（>260）— 移动/还原引擎 | ✅ **本次真实验证通过**：346 字符深路径下 `move_items moved=1 failed=0`、`execute_undo moved=1 failed=0`；`win_long` 前缀在真实文件系统生效 |
| 长路径（>260）— 扫描自动发现 | ⚠️ 未验证：`scanner.scan` 使用 `root.rglob` 遍历，未对遍历路径加 `\\?\` 前缀，>260 深树的自动发现受此限制。属 P1-5 长路径支持的**独立遗留小限制**，超出 Phase 4 范围；移动/还原引擎本身已验证。 |
| 权限错误 | ✅ 已验证（`friendly_message` 映射 + `test_reliability`/`test_p2_coverage T1`） |

**P2-3 修复实录**：真实实验先暴露 `move_items` 在 >260 深路径因目标父目录 `mkdir` 未用 `win_long` 而失败（`WinError 3`）。改为 `os.makedirs(win_long(item.target.parent), exist_ok=True)` 单行修复后，346 字符路径的 `move`+`undo` 全流程真实通过。无伪造 PASS、无 forced skip。

## 9. 构建可复现性（P2-5 / P2-6）

- **P2-6 PASS**：`build.bat` 现统一调用 `build.spec`（含 name/onefile/windowed/hiddenimports/签名占位），消除此前内联参数缺失 hiddenimports 导致两条打包路径产物不一致的风险。
- **P2-5 CONDITIONAL**：`requirements.txt` 已锁 `PySide6==6.7.0` 并补 `pyinstaller==6.11.1`，但**本环境未装 PyInstaller**，版本为候选值并明确标注 `PENDING VERIFICATION`。判定规则：仅当 `requirements + Python + PyInstaller + PySide6 + build.spec` 在真实构建机全部确认后，P2-5 方可转为 PASS。

## 10. 剩余风险

1. **P2-5 构建版本未验证**：PyInstaller 版本为候选值，需在 Phase 5 构建机核对；当前不可判定"构建可复现"为 PASS。
2. **代码签名（P1-4，发布阻断项）**：`build.spec` 仍 `codesign_identity=None`，`build.bat` 仅留条件签名占位（需外部 EV/自签证书）。无证书则 SmartScreen 报"未知发布者"、杀软易误报——属发布阻断，非代码缺陷。
3. **scanner >260 自动发现**：`rglob` 遍历未加长路径前缀，>260 深树自动扫描仍受限（移动/还原引擎已验证）。
4. **`_tmp_home/` 未能删除**：被另一进程持有 OS 文件锁，本会话无法移除；其为测试 sandbox HOME（仅 28KB 测试 db，非生产数据），已加入 `.gitignore`，不影响发布，锁释放后可手动删除。

## 11. Release Candidate 判定

**READY WITH CONDITIONS**

- P2-1/2/3/4/6/7 实做并验证；P0/P1 全量零回归；新增测试 4 组全 PASS；`compileall` PASS。
- 两项 CONDITIONAL 阻断 RC 完全就绪：① P2-5 构建版本待 Phase 5 验证；② 代码签名待外部证书。
- 长路径移动/还原引擎已真实验证通过，仅 scanner 自动发现 >260 深树为独立小限制。

## 12. Phase 5 建议

✅ 进入 **Phase 5（Release Candidate Validation）**，按序执行：
1. 在真实 Windows 构建机：`python --version` / `pyinstaller --version` / 核对 `PySide6` 版本 → 回填 `requirements.txt` → 使 P2-5 转 PASS。
2. `pyinstaller build.spec` 构建 `dist/DesktopCleaner.exe`。
3. EXE 启动冒烟（离屏截图/无崩溃）。
4. 真实目录端到端验证：扫描→预览→整理→撤销（含中文/空格/深层路径样例）。
5. 用户提供代码签名证书后执行 `signtool sign` 消除 SmartScreen。
6. RC 发布评审（P2-5 + 签名两项 CONDITIONAL 关闭后 → **READY FOR RC**）。
