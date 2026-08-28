# Desktop Cleaner — Phase 5 Preflight Report

> 阶段：Phase 5 — Release Candidate Validation / Step 0 (只读环境 + 构建条件检查)
> 原则：真实 Windows 优先 · 真实 EXE 优先 · 真实文件夹优先 · 不伪造版本 · 本步不修改任何产品代码
> 生成时间：2026-08-28

---

## 1. Build Environment

| 项 | 值 | 来源 / 说明 |
|---|---|---|
| 操作系统 | Microsoft Windows 11 专业版 | `systeminfo`: OS 名称=Microsoft Windows 11 专业版 |
| 版本 / Build | 10.0.22631 (Build 22631) | `systeminfo` |
| 内核 / Shell | MINGW64_NT-10.0-22631 (Git Bash) on real NT kernel | `uname -a` |
| 架构 | x86_64 / AMD64 | `PROCESSOR_ARCHITECTURE=AMD64`, `MSYSTEM=MINGW64` |
| 项目路径 | `C:\Users\Administrator\WorkBuddy\2026-08-27-22-10-58\desktop-cleaner` | `pwd` |
| Python（受管） | **3.13.14** | `C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe --version` |
| pip | 26.1.2 | 可用；PyPI 可达（`pip index versions PySide6` 成功） |
| PySide6 | ❌ **未安装** | managed Python 中 `import PySide6` → ModuleNotFoundError |
| PyInstaller | ❌ **未安装** | managed Python 中 `pyinstaller --version` → No module named pyinstaller |

> 结论：本机是**真实 Windows 11**（满足 RULE-1 真实 Windows / RULE-3 真实文件系统）。但构建真实 EXE 所需的 **PySide6 与 PyInstaller 均未安装**，需先建立构建环境。

---

## 2. P2-5 构建版本一致性预检（关键发现）

`requirements.txt` 当前内容：
```
PySide6==6.7.0
pyinstaller==6.11.1   # CANDIDATE / PENDING VERIFICATION
```

实测 `pip install --dry-run PySide6==6.7.0` 输出：
```
ERROR: Ignored ... 6.7.0 Requires-Python >=3.9,<3.13; ...
ERROR: Could not find a version that satisfies the requirement PySide6==6.7.0
```
- **PySide6 6.7.0 无法在 Python 3.13 上安装**（其 `Requires-Python` 上限为 `<3.13`）。
- PyPI 上**最低支持 Python 3.13 的版本为 `6.8.0.2`**（其后 6.8.1 … 6.11.2 均支持）。
- 因此：在**真实构建主机（Python 3.13.14）**上构建真实 EXE，必须将 PySide6 钉版本**提升**到 ≥ `6.8.0.2`。

这与用户既定 P2-5 规则一致（“如果不同：以真实构建环境为准，更新 requirements.txt”）。本环境即为真实构建环境，故应将 PySide6 钉到实际可用版本并回填 `requirements.txt`。

> 同样待验证：PyInstaller 钉 `6.11.1` 能否在 Python 3.13 安装/运行，将在“正式构建”步骤实测后回填。

---

## 3. 构建配置一致性（已读文件）

| 文件 | 检查结论 |
|---|---|
| `build.spec` | 单文件 one-file、windowed、`console=False`、`codesign_identity=None`、hiddenimports 覆盖 core/data/ui/utils/version。作为**唯一构建事实源**结构正确。✅ |
| `build.bat` | 先 `pip install -r requirements.txt` 再 `pyinstaller build.spec`，与 spec 对齐（P2-6 PASS）。✅ |
| `requirements.txt` | PySide6 钉 6.7.0 与宿主 Python 3.13 **不兼容**（见 §2）。⚠️ 需更新。 |
| `main.py` | 启动调用 `reconcile_pending()`（P0-1 恢复护栏）。✅ |
| `src/core` / `src/data` / `src/ui` | Phase 2/3/4 已完成，P0/P1 逻辑冻结、未改表结构。✅（仅读，未改） |

三者（requirements + build.spec + build.bat）在**结构上一致**；唯一需要修正的是 `requirements.txt` 中 PySide6 的钉版本（由真实环境强制决定）。

---

## 4. Git / 工作树状态

```
$ git status
fatal: not a git repository (or any of the parent directories): .git
```

- `desktop-cleaner/` **不是 Git 仓库**（向上查父目录亦无 `.git`）。
- 影响：RC Baseline 无法用 git tag 锚定；将以“报告 + 源码状态描述 + EXE SHA-256 + 测试结果”方式记录基线（等价归档）。
- 不影响构建与真实 EXE 测试。

---

## 5. Step 0 判定

- ✅ **环境真实性**：真实 Windows 11 / x86_64 / 真实文件系统 → RULE-1、RULE-3 满足。
- ⚠️ **构建前置依赖缺失**：PySide6、PyInstaller 未安装。
- ⚠️ **钉版本冲突**：`PySide6==6.7.0` 无法在宿主 Python 3.13 安装 → 需提升到 ≥ `6.8.0.2` 并回填 `requirements.txt`（符合 P2-5 规则）。
- ⚠️ **无 Git 基线**：需以报告形式记录 RC Baseline。
- 🔒 **本步未修改任何产品代码**（仅读取 + 输出本报告）。

---

## 6. 进入下一步的阻塞项 / 决策点

要产出**真实 EXE** 并跑“真实 EXE 测试”（满足用户“禁止只跑源码声称 EXE 通过”的硬要求），必须先解决：

1. **PySide6 钉版本提升**：`6.7.0` → `6.8.0.2`（或更高 3.13 兼容版），并同步 `requirements.txt`。
2. **安装构建依赖**：在受管 Python 的 venv 中 `pip install PySide6==<实际版本> pyinstaller==6.11.1`。
3. **构建真实 EXE**：`pyinstaller build.spec` → `dist/DesktopCleaner.exe`，记录大小 / 时间 / SHA-256。
4. **Git 基线**：建议初始化仓库或至少记录状态（非阻塞，可后续处理）。

以上均属“构建环境准备”，不涉及产品业务逻辑修改。是否按“以真实构建环境为准”提升 PySide6 钉版本并继续真实 EXE 构建，待确认后执行。
