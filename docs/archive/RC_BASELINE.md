# Desktop Cleaner — V1.x RC Baseline

> 建立时间：2026-08-28
> 判定：`## RC READY WITH CONDITIONS`（见 `PHASE5_RC_REPORT.md`）
> 基线性质：**核心代码自此冻结**，仅安全/缺陷修复可回溯修改；发布前须满足条件 A（签名）+ 知悉条件 B（深层扫描）。

---

## 1. 构建环境指纹（不可变）

| 项 | 值 |
|---|---|
| OS | Microsoft Windows 11 专业版 / Build 22631 / x86_64 |
| Python | 3.13.14（受管解释器） |
| PySide6 | 6.8.0.2 |
| PyInstaller | 6.11.1 |
| 构建 venv | `C:\Users\Administrator\.workbuddy\binaries\python\envs\desktop-cleaner-build` |

## 2. 依赖锁版本（requirements.txt）

```
PySide6==6.8.0.2
pyinstaller==6.11.1
```
> 注：原 `6.7.0` 因 `Requires-Python <3.13` 无法在 Python 3.13 安装，按 P2-5 真实环境规则提升到 `6.8.0.2`。

## 3. 构建配置（build.spec 要点）

- 单文件 one-file；`name=DesktopCleaner`；`console=False`（windowed）。
- `codesign_identity=None`（未签名，见条件 A）。
- `hiddenimports` 覆盖：`core`, `data`, `ui`, `utils`, `version`（及子模块）。
- 唯一构建事实源；`build.bat` 与之对齐。

## 4. RC 产物指纹

| 项 | 值 |
|---|---|
| 产物路径 | `dist_rc/DesktopCleaner.exe` |
| 大小 | 46,805,839 bytes（≈ 44.6 MB） |
| SHA-256 | `d5732bf8c8a330705d3e672c3212b7379b7c328986239e1d4c8404b18075d729` |
| 计算方式 | `certutil -hashfile dist_rc/DesktopCleaner.exe SHA256`（真实 Windows） |

> 为何是 `dist_rc/` 而非 `dist/`：旧 `dist/DesktopCleaner.exe` 被 2 个会话前进程（PID 9716/15036，Access Denied 无法终止）锁定，本次构建改输出到 `dist_rc/`。该锁定与产品无关。

## 5. 测试结果（全部真实执行 PASS）

| 类别 | 套件 / 场景 | 结果 |
|---|---|---|
| 自动化 | test_core（手动断言） | ALL TESTS PASSED |
| 自动化 | test_security（pytest） | 4 passed |
| 自动化 | test_reliability（pytest） | 9 passed |
| 自动化 | test_windows_paths（pytest） | 5 passed |
| 自动化 | test_p2_coverage（pytest） | 4 passed |
| 真实文件系统 | test_phase5_e2e（15 场景） | ALL PASSED |
| 静态 | compileall src/tests | exit 0 |
| 真实 EXE | 启动/建库/写日志/干净退出 | PASS（3 次复测一致） |

## 6. 发布条件

- **A（阻断）**：Authenticode 签名。发布前 `signtool sign /fd SHA256 /tr <ts> /td SHA256 dist_rc/DesktopCleaner.exe`，重算 SHA-256。
- **B（限制）**：>260 深层路径 scanner 源发现不支持 `\\?\` 递归（move/undo 引擎已验证可用）；用户须知或后续修复。

## 7. 冻结范围

冻结：`src/core/`、`src/data/`、`src/utils/`、`src/version.py` 业务逻辑与表结构。
未冻结（后续阶段）：UI 迁移审计（Figma → PySide6），属 Phase 5 之后工作。

---
*本基线为 Phase 5 收尾交付物之一，与 `PHASE5_RC_REPORT.md` 配套。*
