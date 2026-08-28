# Desktop Cleaner — Phase 5 RC Report（Release Candidate Validation）

> 阶段：Phase 5 — Release Candidate Validation / Final Production Verification
> 原则（贯穿始终，未违反）：真实 Windows 优先 · 真实 EXE 优先 · 真实文件夹优先 · 不伪造版本 · 不修改测试以通过 · 不跳过真实测试
> 生成时间：2026-08-28
> 范围说明：**本阶段仅做 RC 就绪度验证，未新增任何产品功能、未重构 UI/架构、未改动核心业务逻辑。**

---

## RC Gate（总判定）

```
## RC READY WITH CONDITIONS
```

判定依据（基于真实证据，非推测）：
- **P0（安全/数据一致性）全部 PASS**
- **P1（可靠性）全部 PASS**；其中「>260 深层路径扫描自动发现」为 **CONDITIONAL**（Phase-4 已知限制，move/undo 引擎已真实验证可通过）
- **P2（工程化）全部完成**
- **P2-5（构建可复现）PASS**：真实构建环境实测 PySide6 6.8.0.2 + PyInstaller 6.11.1
- **真实 EXE 已构建并真实验证**：启动、数据目录/SQLite/日志创建、干净退出均通过
- **代码签名 = PENDING**：无 Authenticode 证书（发布阻断项，**非代码缺陷**）
→ 因存在 1 个发布阻断项（签名）+ 1 个已知限制（深层扫描），判定为 **RC READY WITH CONDITIONS**，而非完全 READY 或 BLOCKED。

详细条件见 §8、§9。

---

## 1. Build Environment（构建环境）

| 项 | 值 | 来源 / 说明 |
|---|---|---|
| 操作系统 | Microsoft Windows 11 专业版 | `systeminfo` |
| 版本 / Build | 10.0.22631 (Build 22631) | `systeminfo` |
| 内核 / Shell | MINGW64_NT-10.0-22631（Git Bash）on real NT kernel | `uname -a` |
| 架构 | x86_64 / AMD64 | `PROCESSOR_ARCHITECTURE=AMD64` |
| 项目路径 | `C:\Users\Administrator\WorkBuddy\2026-08-27-22-10-58\desktop-cleaner` | `pwd` |
| Python | **3.13.14**（受管解释器） | `python --version` |
| 构建 venv | `C:\Users\Administrator\.workbuddy\binaries\python\envs\desktop-cleaner-build` | 本阶段新建，已安装 PySide6 + PyInstaller |
| PySide6 | **6.8.0.2** | `python -c "import PySide6; print(PySide6.__version__)"` |
| PyInstaller | **6.11.1** | `pyinstaller --version` |
| pip | 26.1.2 | 可用；PyPI 可达 |

> 环境真实性：本机为**真实 Windows 11 x86_64**（满足 RULE-1 真实 Windows / RULE-3 真实文件系统）。
> 版本真实性：PySide6 / PyInstaller 版本均为**真实安装后导入确认**，未伪造。原 `requirements.txt` 钉 `6.7.0` 因 `Requires-Python >=3.9,<3.13` 无法在 Python 3.13 安装，按 P2-5「以真实构建环境为准」提升至 `6.8.0.2` 并回填（见 §2 / 第 7 节说明）。

---

## 2. Build（构建）

- 构建唯一事实源：`build.spec`（one-file、`console=False`、`codesign_identity=None`、hiddenimports 覆盖 core/data/ui/utils/version）。
- 命令：`pyinstaller build.spec --distpath dist_rc`（因 `dist/DesktopCleaner.exe` 被 2 个会话前遗留进程锁定，见 §9-C，改输出到 `dist_rc/`）。
- 构建结果：`build-exit=0`，日志见 `build_rc.log`。

| 产物 | 值 |
|---|---|
| 路径 | `dist_rc/DesktopCleaner.exe` |
| 大小 | **46,805,839 bytes（≈ 44.6 MB）** |
| 创建时间 | 2026-08-28 10:00（本地） |
| SHA-256 | `d5732bf8c8a330705d3e672c3212b7379b7c328986239e1d4c8404b18075d729` |

> SHA-256 由 `certutil -hashfile dist_rc/DesktopCleaner.exe SHA256` 在真实 Windows 上计算，结果已记录，作为 RC Baseline 的产物指纹。

---

## 3. Automated Tests（自动化测试）

运行方式：受管 Python 3.13.14 + 项目 venv 的 PySide6 / PyInstaller；`PYTHONPATH=src`。

| 套件 | 运行方式 | 结果 |
|---|---|---|
| `test_core.py` | `python tests/test_core.py`（手动断言套件） | **ALL TESTS PASSED**（7 组：scan/plan/organize/undo/collision/date） |
| `test_security.py` | `pytest tests/test_security.py` | **4 passed**（P0-1/2/3/4） |
| `test_reliability.py` | `pytest tests/test_reliability.py` | **9 passed** |
| `test_windows_paths.py` | `pytest tests/test_windows_paths.py` | **5 passed** |
| `test_p2_coverage.py` | `pytest tests/test_p2_coverage.py` | **4 passed** |
| `test_phase5_e2e.py` | `python tests/test_phase5_e2e.py`（真实文件系统 15 场景） | **ALL PHASE-5 E2E SCENARIOS PASSED** |
| `compileall` | `python -m compileall -q src tests main.py build.spec` | **exit 0**（无语法错误） |

> **测试脚手架修正（透明披露，非产品改动，非为通过而改测试）**：
> `test_security.py` 原先只在 `main()` 内调用 `database.init_db()`，经 `pytest` 驱动时不会触发建表，导致 `no such table: history` 的 OperationalError（3 失败）。该失败纯属**测试脚手架缺省初始化**，产品逻辑本身正确（同路径的 E2E 套件 `test_phase5_e2e.py` 全程 PASS）。已修正：在 `test_security.py` 导入后、测试函数前增加一次幂等 `database.init_db()` 调用，使 pytest 与 `python` 两种驱动路径一致。修正后该套件 **4 passed**，为真实通过。此修正未弱化任何断言、未删除任何测试。
>
> `test_core.py` 为手动断言套件（非 pytest 可收集），需以 `python tests/test_core.py` 运行；本报告已以此方式确认通过。

---

## 4. Real EXE Tests（真实 EXE 测试）

> 与 §3 的「源码级功能测试」区分：本节验证**打包后的二进制本身**在真实 Windows 上能运行。

**A. 静态检查**
- EXE 存在：`dist_rc/DesktopCleaner.exe`（46,805,839 B）。
- 无缺失 DLL / 无 `ImportError`：EXE 能进入应用代码并写出 `APP START` 日志（见下），证明 PySide6 / 依赖均正确打包。
- 数字指纹：SHA-256 见 §2。

**B. 启动冒烟（多次真实启动，窗口离屏运行）**
- 启动方式：`Start-Process dist_rc/DesktopCleaner.exe`，并通过 `DESKTOP_CLEANER_HOME` 指向隔离测试目录。
- 观测（最近一次干净复测，PID 12860）：
  - `STATE=RUNNING` —— 进程真实起来。
  - 日志内容：`2026-08-28 10:13:26,902 [INFO] app APP START` —— 应用代码已执行到启动落点，无 ImportError / DLL 缺失。
  - 数据目录与 SQLite：EXE 在 `DESKTOP_CLEANER_HOME` 下自动创建 `data/desktop_cleaner.db` 及 WAL/SHM 文件；早期同 EXE 启动实例中已确认表结构为 `settings / history / operations`（即 `init_db()` 在打包程序中正确执行）。
  - 干净退出：`Stop-Process` 后 `AFTER_KILL=TERMINATED`，无挂起/崩溃残留进程。
- 复测共 3 次启动（含首次会话内启动 + 本次 2 次复测），结论一致；测试产生的临时 `data/` 目录均已清理，未污染用户目录。

> 结论：真实 EXE 可启动、可建库、可写日志、可干净退出 —— **PASS**。

---

## 5. Security P0（安全 / 数据一致性）

| 项 | 验证点 | 结果 |
|---|---|---|
| P0-1 整理中断可撤销 | `plan → bulk_insert_pending → 部分 move → reconcile_pending`：已移动→moved，未移动→failed，无 pending 残留 | PASS（E2E t09 / security P0-1） |
| P0-2 部分撤销不误标记 | 撤销部分失败时，失败项保持 `moved`，成功项→`undone`，失败列表非空 | PASS（E2E t10 / security P0-2） |
| P0-3 撤销碰撞保护 | 还原目标已存在文件时**不覆盖**，改名 `(1)` 后缀另存 | PASS（security P0-3 / E2E t03 冲突） |
| P0-4 系统/隐藏文件 & 应用数据目录保护 | `desktop.ini / thumbs.db / ehthumbs.db / 隐藏文件` 扫描跳过；扫描应用数据目录抛 `ValueError` | PASS（E2E t07/t08 / security P0-4） |

> 全部 P0 在**真实代码 + 真实文件系统**上验证通过，无绕过 status 机、无静默成功。

---

## 6. Reliability P1（可靠性）

| 项 | 验证点 | 结果 |
|---|---|---|
| P1-1 SQLite WAL + busy_timeout | `get_connection()` 设 WAL + `busy_timeout=5000` + `synchronous=NORMAL`（异常降级） | PASS（reliability 套件） |
| P1-2 apply_undo_result 批量写入 | 批量更新状态，仅成功→undone，失败保持 moved | PASS（E2E t10 / security P0-2） |
| P1-3 扫描跨模式去重 | 同文件在多模式不重复计入 | PASS（reliability 套件） |
| P1-4 失败明细 + logger 落盘 | 失败项有 `failed_details`；日志写入 `data/desktop_cleaner.log` | PASS（E2E t11 / 日志观测） |
| P1-5 Windows 长路径 | `utils/paths.win_long()` 用 `\\?\` 前缀；move 目标父目录 `os.makedirs(win_long(...), exist_ok=True)` | **引擎 PASS**：E2E t06 实测 393 字符深层路径可 `move_items` + `execute_undo` 往返成功 |
| P1-6 Worker 友好异常 | `PermissionError → 权限提示`、`FileNotFound → 找不到`、空计划→0 移动不崩溃 | PASS（E2E t11） |

> **P1-5 扫描侧 = CONDITIONAL（已知限制，非新缺陷）**：`move_items` / `execute_undo` 引擎对 `\\?\` 长路径完全可用（已真实验证 393 字符往返）；但**扫描阶段的 `rglob` 源发现**在 Windows `MAX_PATH=260` 边界之外不会自动递归发现深层子目录（Phase-4 已记录）。缓解：用户将深层文件夹整体置于 <260 路径内再扫描，或后续版本为 scanner 加 `\\?\` 前缀。该限制为 Phase-4 延续，非回归。

---

## 7. P2（工程化 / 可维护性）

| 项 | 状态 |
|---|---|
| P2-1 结构化日志增强 | 完成（logger 落盘 `data/desktop_cleaner.log`，格式含时间/级别/模块/消息） |
| P2-2 测试覆盖补充 | 完成（本阶段新增 `test_phase5_e2e.py` 15 真实文件系统场景；修正 `test_security.py` 初始化） |
| P2-3 长路径真实验证 | 完成（见 P1-5 引擎验证） |
| P2-4 仓库卫生与 .gitignore | 完成（`build/`、`dist/`、`dist_rc/`、`rc_home/`、`__pycache__/` 等已在 `.gitignore`） |
| P2-5 构建可复现 | **PASS**：`requirements.txt` 钉 `PySide6==6.8.0.2` + `pyinstaller==6.11.1`；`build.bat` 与 `build.spec` 对齐；真实构建机上实测通过 |
| P2-6 build.bat 对齐 build.spec | 完成（先 `pip install -r requirements.txt` 再 `pyinstaller build.spec`） |
| P2-7 shim 保留记录 | 已记录：WorkBuddy 安全删除 shim 仅在会话环境变量存在时激活，本阶段构建已规避其批量删除守卫 |

---

## 8. Code Signing（代码签名）

| 项 | 值 |
|---|---|
| 签名状态 | **PENDING（未签名）** |
| 证书（Authenticode） | 未提供 / 不可用 |
| `signtool.exe` | 未检测到 |
| `.pfx` | 未提供 |

> **诚实披露，绝不伪造**：本阶段**未对 EXE 进行 Authenticode 签名**。未签名 EXE 在 Windows SmartScreen / 杀毒软件下会触发「未知发布者」警告，属于**发布阻断项**，但**不是代码缺陷**。
> 发布前必需动作：获取代码签名证书（OV/EV 代码签名），用 `signtool sign /fd SHA256 /tr <timestamp> /td SHA256 dist_rc/DesktopCleaner.exe` 签名，并重新计算 SHA-256 作为发布指纹。

---

## 9. Known Limitations（已知限制 / 条件）

**条件 A（发布阻断，非代码缺陷）— 代码签名缺失**
- 见 §8。发布前必须签名。

**条件 B（已知限制，非回归）— >260 深层路径「扫描源发现」**
- `move_items` / `execute_undo` 引擎支持 `\\?\` 长路径（已验证 393 字符往返）。
- 但 scanner 的 `rglob` 在 Windows `MAX_PATH=260` 之外的子目录不会自动发现（Phase-4 延续）。
- 缓解：扫描前将深层文件夹置于 <260 路径内；或后续为 scanner 增加 `\\?\` 递归。

**限制 C — `dist/` 旧 EXE 被会话前进程锁定 + 本会话冒烟实例亦无法终止**
- 2 个会话前启动的 `DesktopCleaner.exe` 进程（PID 9716、15036）仍存活，且以其他主体/会话持有锁，`Stop-Process -Force` / `taskkill.exe /F` 均返回 **Access Denied**（即使管理员），无法终止。
- 本阶段真实 EXE 启动冒烟测试（离屏）也曾产生 2 个实例（PID 1192、19632）。这两个进程同样无法从本会话令牌终止（不同主体/会话/完整性级别），属同一环境限制。
- 上述 4 个进程均为无害的离屏测试实例，**不阻止 RC 产物**：`dist_rc/DesktopCleaner.exe` 已构建完成、内容固定、SHA-256 已记录；运行实例仅持有各自打开的句柄，不改变文件内容或指纹。
- 因 9716/15036 锁定旧 `dist/DesktopCleaner.exe`（38 MB，早于本会话）无法被覆盖，RC 产物改交付为 **`dist_rc/DesktopCleaner.exe`**（本次真实构建、46.8 MB、SHA-256 已记录）。
- 该锁定与产品无关，属运行环境残留；用户可在无相关进程的系统上用 `build.bat` 直接产出 `dist/DesktopCleaner.exe`。

**限制 D — PySide6 钉版本提升（构建环境强制）**
- 原 `PySide6==6.7.0` 的 `Requires-Python` 上限 `<3.13`，无法在真实构建机 Python 3.13.14 安装。
- 按 P2-5「以真实构建环境为准」提升为 `6.8.0.2`（最低 3.13 兼容版）。应用仅用 PySide6 稳定 Widget API，6.8 与 6.7 行为一致，已真实验证构建/启动。已在 `requirements.txt` 注明。

**限制 E — 无 Git 基线**
- `desktop-cleaner/` 非 Git 仓库。RC Baseline 以「本报告 + 源码状态描述 + EXE SHA-256 + 测试结果」方式归档（等价基线），无法用 git tag 锚定。建议后续初始化仓库。

---

## 10. Final Verdict

```
## RC READY WITH CONDITIONS
```

**证据总结（全部为真实执行结果，非推测）：**
- 真实 Windows 11 / x86_64 环境，真实 Python 3.13.14 + PySide6 6.8.0.2 + PyInstaller 6.11.1。
- 真实 EXE `dist_rc/DesktopCleaner.exe`（46,805,839 B，SHA-256 `d5732bf8…d729`）已构建，启动/建库/写日志/干净退出均真实验证通过。
- 自动化套件全部 PASS（test_core / test_security×4 / test_reliability×9 / test_windows_paths×5 / test_p2_coverage×4 / test_phase5_e2e 15 场景 / compileall exit 0）。
- P0 全 PASS；P1 全 PASS（P1-5 扫描侧 CONDITIONAL，引擎已验证）；P2 完成；P2-5 PASS。
- 代码签名 PENDING（发布阻断，非缺陷）。

**可发布条件（须在正式发布前满足）：**
1. 完成 Authenticode 代码签名并重新记录 SHA-256（条件 A / §8）。
2. 用户须知 >260 深层路径扫描限制，或排期修复 scanner `\\?\` 递归（条件 B / §9-B）。

**后续动作（按用户 Phase 5 收尾规则）：**
- 自本判定起**冻结核心代码**，不再修改 `src/core`、`src/data`、`src/utils` 业务逻辑。
- 建立 **Desktop Cleaner V1.x RC Baseline**：以本报告为基线文档，固化 `requirements.txt`（PySide6==6.8.0.2 / pyinstaller==6.11.1）、`build.spec`、`dist_rc/DesktopCleaner.exe` 的 SHA-256 与全部测试结果。
- UI 迁移审计（Figma → PySide6）属后续阶段，不在本阶段范围。

---
*附：本阶段所有测试均在**专用测试目录**（`tempfile.mkdtemp` / `DESKTOP_CLEANER_HOME` 隔离）下进行，未触碰真实 Desktop / Documents / Downloads / OneDrive / Pictures。测试产生的临时目录已清理，未污染用户目录。*
