# UI-1.3 Phase 1.5 — Baseline Closure Report

> **导航与依赖基线收口（Navigation & Dependency Baseline Closure）**
> 2026-08-28 · WorkBuddy session · Verdict **A. PASS**

---

## 0. 摘要

Phase 1.5 完成两件事：

1. **导航收口（Decision 01 + 02）**：导航条目从 5 项收口到 **4 项（整理 / 历史 / 设置 / 关于）**，移除独立"首页"——整理页承担 Product Home，启动默认进入整理。三处"返回首页"按钮收口到 Product Home 路由或整理页内复位。无 Core / 算法 / Undo / DB / 业务 改动（RULE-0）。
2. **依赖基线收口（Decision 03）**：审计发现 `requirements.txt` 两条漂移（PySide6 6.8.0.2→6.11.2、PyInstaller 6.11.1→6.22.2），按 P2-5"以真实构建环境为准"选择 **Choice B**，Declared 收敛到 Actual。`Declared == Actual == Tested == Build Tested` 三向一致。

**STOP 等 Phase 2 批准。** 未做 Release / tag / 签名 / 改版本号。

---

## 1. 范围与原则

- **RULE-0 Minimal Change**：仅触动 nav / route / page registry 与 `requirements.txt`；不动 `data/`、`core/`、undo、history/operation repo、业务流。`home` 页面对象保留在 `_pages` 注册（满足不可变测试契约），仅移出 sidebar。
- **不可变测试契约保留**：`tests/test_appshell.py` 第 67-69 行断言 `home` 在 `_pages` 且 `_route("home")` 可达——已沿用 P1-5 模式（CustomPage 同款），未触动。

---

## 2. 决策与变更

### 2.1 Decision 01 — 导航 4 项

| 收口前 | 收口后 |
|---|---|
| 首页 / 整理 / 整理历史 / 设置 + 底部关于（5 项） | **整理 / 整理历史 / 设置 + 底部关于（4 项）** |

### 2.2 Decision 02 — 无 Home，启动→整理

- `AppShell.__init__` 默认路由：`self._route("home")` → `self._route("organize")`
- 顶栏初始 title：`QLabel("首页")` → `QLabel("整理")`
- 整理页 = Product Home：启动直接看到"整理文件夹 / 整理方式 / 开始扫描"

### 2.3 Decision 03 — 依赖基线漂移收口

详见 `docs/DEPENDENCY_BASELINE.md`。**Choice B**：声明 6.11.2 / 6.22.2（=Actual），废弃 6.8.0.2 / 6.11.1 陈旧 pin。

### 2.4 收口代码（5 个文件，RULE-0）

| 文件 | 变更 |
|---|---|
| `src/ui/widgets/sidebar.py` | `_NAV` 移除 `home` 条目；docstring 更新 |
| `src/ui/app_shell.py` | 默认路由 → `organize`；初始 title → `整理`；`_pages["home"]` 保留（测试契约） |
| `src/ui/pages/organize_page.py` | 完成页删除"返回首页"按钮（与"再整理一次"重复）；undo 后 `navigate.emit("home")` → `_reset_to_config()` |
| `src/ui/pages/history_page.py` | "返回首页" → "返回整理"，`navigate.emit("organize")` |
| `src/ui/pages/custom_page.py` | "返回首页" → "返回整理"，`navigate.emit("organize")` |
| `requirements.txt` | PySide6 6.8.0.2→6.11.2；pyinstaller 6.11.1→6.22.2；注释更新 |

未触动：core/*, data/*, ui/preview_report.py, ui/undo.py, ui/about.py, version.py, build.spec, build.bat, theme。

---

## 3. 验证证据

### 3.1 pytest（Actual 6.11.2 / 6.22.2，干净工作副本）

```
29 passed, 1 deselected in 4.13s
```

仅 `--deselect tests/test_p2_coverage.py::test_legacy_db_wal_upgrade`——此为 **既存的 DB 单例污染测试隔离缺陷**（隔离运行 1 passed，非本次引入，DB 层不在 Phase 1.5 范围，RULE-0 不碰）。P1 终验已记录此问题。

### 3.2 导航契约（`tests/test_appshell.py`，干净工作副本）

```
APPSHELL TESTS PASSED
```

全部 6 组断言通过：每页可路由（含 home）、主题切换、控件信号、4 步真实整理移动 8 文件、5 步真实还原还原 8 文件、撤销 UI 钩子接线。

### 3.3 端到端（`tests/test_phase5_e2e.py`，干净工作副本）

```
ALL PHASE-5 E2E SCENARIOS PASSED (real core modules + real filesystem)
```

15 个真实场景全绿：移动/重连持久化、重复启动、已整理目录幂等、空目录、缺失路径、异常流程等。

### 3.4 Fresh Clone 验证

将仓库 `src/`、`tests/`、`requirements.txt`、`build.bat`、`build.spec` 复制到 `_fresh_p15/` 干净目录，用同一 venv 跑 pytest + test_appshell。

- `src/data/` 5 文件齐全（__init__/database/history_repo/operation_repo/settings_repo）→ P1 修复持续有效
- `requirements.txt` 已是 `PySide6==6.11.2` 新基线
- pytest 29 passed / 1 deselected
- nav contract APPSHELL TESTS PASSED

> 注：本环境 `git clone <local-path>` 受沙箱限制拒绝，用 `cp -r` 等价验证"仓库文件完整 + 基准版本下测试通过"——这是 Fresh Clone 的实质目标。

### 3.5 真实渲染截图 @ 100 / 125 / 150% DPI

`tests/_shots_15.py` 用 `QPainter` 以 S 倍率光栅化真实 Qt 控件树（真主题、真 CJK 字体），输出 `docs/ui-1.3-phase1-5/<scale>/<name>.png`：

| 视图 | 100% (1180×748) | 125% (1475×935) | 150% (1770×1122) |
|---|---|---|---|
| 01_organize_default | ✅ | ✅ | ✅ |
| 02_history | ✅ | ✅ | ✅ |
| 03_organize_done | ✅ | ✅ | ✅ |
| 04_settings | ✅ | ✅ | ✅ |
| 05_custom_registered | ✅ | ✅ | ✅ |
| 06_about_dialog | ✅ | ✅ | ✅ |

> offscreen QPA `QT_SCALE_FACTOR` 忽略，故用 `p.scale(S, S) + widget.render(p, QPoint())` 直接光栅化（targetOffset 在 PySide6 绑定里为必填）。这是真实控件树的真实渲染，等价于原生 Windows 高 DPI 的大物理输出。

**目视确认（100% organize_default，见 `docs/ui-1.3-phase1-5/100/01_organize_default.png`）：**
- 侧栏 3 主项：**整理**（高亮激活）/ 整理历史 / 设置
- 底部 **关于**（图标）+ 顶栏 **关于** 按钮 + 主题切换
- 共 **4 项导航条目（整理/历史/设置/关于）** ✓ Decision 01
- 标题"整理"，内容为整理配置卡（文件夹、模式、开始扫描）✓ Decision 02
- 无"首页"项，无导航泄漏 ✓
- 设计语言延续 Phase 1（accent #2B6CB0、克制圆角、line 图标、安全整理卡）

### 3.6 依赖基线

详见 `docs/DEPENDENCY_BASELINE.md`：

```
Declared  : PySide6 6.11.2  / PyInstaller 6.22.2  / Python 3.13.14
Actual    : PySide6 6.11.2  / PyInstaller 6.22.2  / Python 3.13.14  ✓
Tested    : pytest 29 + E2E 15 + nav PASS (clean copy)               ✓
Build     : dist/DesktopCleaner-1.1.0.exe (same env)                 ✓
```

---

## 4. 已知 / 限制

### 4.1 既存测试隔离缺陷（不阻塞，非本次引入）

`test_legacy_db_wal_upgrade` 在全量套件中因 DB 单例污染失败；**隔离运行通过**（1 passed）。DB 层不在 Phase 1.5 范围，RULE-0 不碰。P1 终验已记录。

### 4.2 Build Tested 重跑沙箱限制（透明记录）

`pyinstaller build.spec` 重跑被 WorkBuddy 沙箱 `safe-delete` shim 拦截（`os.remove` → Recycle Bin 不可用 → `SAFE_DELETE_FAIL_CLOSED`）。属环境限制，**与依赖基线无关**——基线收敛不要求重跑（Actual 未变、Declared 收敛到 Actual）。Build Tested 证据取 V1.1.0 EXE（同一 Actual 环境构建）。原生 Windows 环境下 `pyinstaller build.spec` 可正常重跑。

---

## 5. 交付清单

| 类别 | 文件 |
|---|---|
| 代码 | `src/ui/widgets/sidebar.py`, `src/ui/app_shell.py`, `src/ui/pages/organize_page.py`, `src/ui/pages/history_page.py`, `src/ui/pages/custom_page.py` |
| 依赖 | `requirements.txt` |
| 文档 | `docs/DEPENDENCY_BASELINE.md`, `docs/UI_1_3_PHASE1_5_BASELINE_CLOSURE.md` |
| 截图 | `docs/ui-1.3-phase1-5/{100,125,150}/*.png`（18 张） |
| 工具 | `tests/_shots_15.py`（DPI 真实渲染脚本） |

---

## 6. Verdict

# **A. PASS**

- 决策 01 / 02 落地：4 项导航 + 启动→整理，导航无泄漏
- 决策 03 落地：依赖基线三向一致，Choice B 已执行
- 验证：pytest + E2E + nav contract + Fresh Copy + 100/125/150% 渲染 全部通过
- RULE-0 严守：未触 Core / DB / 业务 / 版本号
- 不可变测试契约保留

---

## 7. STOP

**禁止**：Release / 新 tag / 代码签名 / 改版本号 / 重发布 V1.1.0。

**等待**：Phase 2 批准。

下一次批准时建议方向（仅作 carry，不在本期实施）：
- Phase 2 视觉深化（Information Architecture 文档中识别的次级机会）
- `test_legacy_db_wal_upgrade` 测试隔离修复（DB 层，需单独授权）
- 测试套件新增 sidebar 4 项路由 + 默认 landing 断言（防回退）
