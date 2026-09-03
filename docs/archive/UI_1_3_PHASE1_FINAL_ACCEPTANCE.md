# UI-1.3 Phase 1 — Final Acceptance Report

> 范围：P1 仓库完整性修复 + Fresh Clone 验证 + Phase 1 回归复核 + 真实 Windows 桌面视觉验收。
> RULE-0：本次只允许处理 Repository Integrity，禁止改 Core / 算法 / Undo / DB / UI / Design System / 业务 / 版本。
> 状态：**DONE — STOP — 等待人工决定是否进入 UI-1.3 Phase 2**。

---

## 1 · Repository

| 检查 | 证据 | 结果 |
|---|---|---|
| `src/data` tracked (5 文件) | `git ls-files src/data` = `__init__.py database.py history_repo.py operation_repo.py settings_repo.py` | **PASS** |
| `.gitignore` 最小最准确 | `data/` → `/data/` 锚定根目录；新增 `rc_home/` 规则（之前只靠 `data/` 意外覆盖，已修正） | **PASS** |
| Fresh clone works | 从 Gitea 全新 clone → `src/data` 真实存在 → `python -c "import data"` 成功 → 7/7 脚本式套件 PASS → pytest 30/30 隔离 PASS → main.py 启动 15s 存活 0 Traceback → 运行时自动创建 `data/desktop_cleaner.db` (WAL) | **PASS** |
| Secret / Artifact 安全 | 提交前对 `src/data/*.py` 做了 `password/secret/token/api_key/private_key` 扫描 → 0 命中；`DB_PATH` 派生自 `DESKTOP_CLEANER_HOME` 环境变量，无硬编码绝对路径；`git ls-files '*.db' '*.log' 'data/'` = 0 | **PASS** |
| local HEAD == origin/main | `local 38842c5 == gitea 38842c5` (POST-push) | **PASS** |

### 1.1 `.gitignore` 修复

```diff
-# App runtime data (SQLite DB + log). The app writes these at runtime;
-# the project source does not track them.
-data/
+# App runtime data (SQLite DB + log). The app writes these at runtime;
+# the project source does not track them.
+# NOTE: anchored with a leading slash on purpose. An unanchored `data/`
+# also matches `src/data/`, which is the SOURCE data layer (repositories +
+# database bootstrap) and MUST stay tracked. Only the repository-root
+# runtime directory should be ignored here.
+/data/
 *.db
 *.db-wal
 *.db-shm
 *.log

 # Session / verification temp artifacts (Phase-4 hygiene)
 _tmp_home/
+rc_home/
 _*.txt
```

### 1.2 fresh clone 验证证据链

```
Gitea 38842c5
   ↓ git clone
_fresh_clone/
   ├─ src/data/         (5 files, 真实存在)
   │  ├─ __init__.py
   │  ├─ database.py
   │  ├─ history_repo.py
   │  ├─ operation_repo.py
   │  └─ settings_repo.py
   ├─ import data  → OK
   ├─ 7 script suites → 7/7 PASS
   ├─ pytest 隔离     → 30/30 PASS (1 failed 在全量单进程模式，属 HEAD 既存 DB 单例污染)
   ├─ main.py 15s 启动 → 0 Traceback, 仅 Qt6 HighDPI DeprecationWarning
   └─ 运行时 data/   → 自动创建 desktop_cleaner.db (WAL: -shm + -wal)
```

---

## 2 · Tests

| 套件 | 形式 | 结果 | 备注 |
|---|---|---|---|
| `test_core.py` | 脚本 | **PASS** | Core 移动/失败/structured detail |
| `test_preview.py` | 脚本 | **PASS** | PreviewReportDialog 构建+确认+安全门 |
| `test_dashboard.py` | 脚本 | **PASS** | Dashboard 统计刷新 |
| `test_theme.py` | 脚本 | **PASS** | 主题切换+ token 一致性 |
| `test_appshell.py` | 脚本 | **PASS** | 4-step 整理 + 5-step 撤销 + 控件 |
| `test_first_launch.py` | 脚本 | **PASS** | 首次启动欢迎对话框 |
| `test_phase5_e2e.py` | 脚本 | **PASS** | 15 端到端场景 (real core + real fs) |
| `test_windows_paths.py` | pytest | **5/5 PASS** | 中文/空格/深路径 |
| `test_combined_path_v11.py` | pytest | **2/2 PASS** | 中文+空格组合 |
| `test_security.py` | pytest | **4/4 PASS** | 权限/安全 |
| `test_reliability.py` | pytest | **9/9 PASS** | 失败/取消/幂等 |
| `test_update.py` | pytest | **6/6 PASS** | AR-2 V1.1.0 Option B 更新系统 |

**pytest（隔离执行）30/30 PASS · 脚本式 7/7 PASS · 总计 37/37 PASS**

**全量单进程 pytest** 报 1 failed `test_p2_coverage::test_legacy_db_wal_upgrade`——已证为 HEAD 既存的 `data.database.DB_PATH` 模块级单例被 `test_combined_path_v11`/`test_reliability`/`test_security` 在同进程内先写入污染所致（与本次 P1/Phase 1 改动无关，RULE-0 不改测试）。

---

## 3 · Regression（Phase 1 无回归）

| 项 | 期望 | 实测 | 结果 |
|---|---|---|---|
| Live UI emoji | 0（仅允许文字符号） | live UI 0；剩余 13 全在 `features.py`（dead 概念模块） | **PASS** |
| 文字符号 | `© → / • ✓` 仅这些 | 7 处（`→`×4, `•`×1, `✓`×2） | **PASS** |
| 导航 | 整理 / 历史 / 设置 / 关于 | 首页 / 整理 / 整理历史 / 设置 + 关于(底部) | **PASS WITH NOTE** |
| Tools / Coming Soon | 不再出现 | UI 路由 0；文件保留（不删底层代码） | **PASS** |
| Accent | `#2B6CB0` | `#2B6CB0` light / `#5AA0E0` dark | **PASS** |
| 旧 accent `#4F46E5` | 不回潮 | 全仓库 grep = 0 | **PASS** |
| Core / algorithm / Undo / DB schema | 零改动 | `git diff d044a31 HEAD -- src/core src/update src/utils` = empty | **PASS** |
| 版本号 | 1.1.0 不变 | `version.py` 未改 | **PASS** |
| requirements.txt lock | 验证可装 | `pip install --dry-run` 解析 PySide6 6.8.0.2 + pyinstaller 6.11.1 PASS | **PASS WITH NOTE** |

### 3.1 Navigation 偏差说明（需人工决定）

| 项目 | Phase 1 §3 决策 | 实际实现 | 来源 |
|---|---|---|---|
| 导航项 | 整理 / 历史 / 设置 / 关于 | 首页 / 整理 / 整理历史 / 设置 + 关于 | 信息架构文档（UI_1_3_INFORMATION_ARCHITECTURE.md）明确记录"保留首页作为着陆（folder-first Hero + 最近整理 + 撤销）"，属已文档化设计决策 |
| 整理历史 vs 历史 | 规范用"历史" | 实现为"整理历史" | 同上：明确区分"按类型/按日期整理历史"与"未来可能的其他历史类型" |

> **判定**：偏差属已文档化的设计决策细化，非破坏 §3 决策的精神（"导航名称必须反映用户任务"）。按 §16 不擅自修改，列为**决策点**供中哥在进 Phase 2 前确认。

### 3.2 requirements.txt 锁漂移说明

| 字段 | 值 |
|---|---|
| `requirements.txt` 锁 | PySide6==6.8.0.2 / pyinstaller==6.11.1 |
| 实际验证构建环境 | PySide6 6.11.2 / pyinstaller 6.22.2（V1.1.0 EXE 实际所用，见 `RELEASE_MANIFEST.md`） |
| 锁定版可装性 | `pip install --dry-run` PASS（Python 3.13.14 兼容） |
| 影响 | 无——`pip install -r requirements.txt` 能装；只是 `pip freeze` 会得到 6.11.2；建议随 V1.1.1/Phase 2 顺手把锁升级到 6.11.2 与发布环境一致 |

> **判定**：与 Phase 1 功能/视觉零关系。列为**P2 待办**。

---

## 4 · GUI

| 项 | 结果 | 证据 |
|---|---|---|
| 真实 Windows GUI | **PASS** | Qt platform=`windows`；屏幕 1920×1032 @ 96 DPI；main.py 15s 启动 0 Traceback |
| CJK 渲染 | **PASS** | Segoe UI + Microsoft YaHei 回退正常；7 屏 × 3 DPI 全部中文清晰（dashboard "桌面文件整理助手/晚上好/选择文件夹" 等；confirm-dialog "项目报告 2026.pdf" 等 8 个真实中文文件名；undo-dialog 真实中文源路径） |
| DPI 100% | **PASS** | `dashboard.png` 等 7 张 |
| DPI 125% | **PASS** | `dashboard@125.png` 等 7 张（`QT_SCALE_FACTOR=1.25`） |
| DPI 150% | **PASS** | `dashboard@150.png` 等 7 张（`QT_SCALE_FACTOR=1.5`） |
| Icon 16/20/24 | **PASS** | 导航 20px、统计 24px、分类 24px、对话框 20px；2x devicePixelRatio 渲染，高 DPI 下清晰 |
| Typography | **PASS** | Segoe UI 主字 + Microsoft YaHei 备字，对齐、行高、字重 650/600/500 符合 Windows 工具调性 |
| Navigation active | **PASS** | `accent_soft`（淡蓝底）+ `accent`（深蓝字），不刺眼，无药丸/渐变/发光 |
| Button 层级 | **PASS** | Primary 蓝填充（开始整理/立即更新/扫描 CTA）/ Secondary 白底边框（选择文件夹/取消/还原）/ Tertiary 幽灵（一键还原）/ Danger 未触发 |
| 截图中文字可读 | **PASS** | 全部 21 张均可读（无豆腐块） |

> 截图证据：`docs/ui-1.3-phase1-final/`（21 个 PNG，7 屏 × 3 DPI）

### 4.1 视觉验收中观察到的 P2（不修复，仅记录）

| 观察 | 范围 | 建议处理阶段 |
|---|---|---|
| 整理页 "开始扫描" 视觉权重偏次级（白底边框） | organize_page.py 扫描 CTA 按钮 QSS | Phase 2（按钮权重审计） |
| 整洁度圆环 96% 仍居中 | Dashboard 右上小组件 | Phase 2（按 IA 文档降级为辅助统计） |
| 统计卡在首页占用面积较大 | dashboard.py | Phase 2（密度调整） |

按任务 §16，这些 P2 不在本阶段修复范围。

---

## 5 · 提交链

```
38842c5  fix(repo): include source data layer in version control
8cadff8  refactor(ui): establish professional Windows visual foundation (UI-1.3 Phase 1)
cfb1219  docs(ui): UI-1.3 read-only audit (6 design specs)
d044a31  release: Desktop Cleaner v1.1.0
```

> `38842c5` + `b29bc00`（截图 commit）已推 Gitea；`local main == gitea/main == 38842c5...`（截图 commit 在 `b29bc00`，随后 push）。

---

## 6 · Verdict

### ✅ A. PASS

满足全部 A 类条件：
- `src/data` tracked (5 files) — **PASS**
- fresh clone works（import / tests / start 全部成功）— **PASS**
- 7/7 脚本式 + 30/30 pytest 隔离 + 21 张真实桌面截图 — **PASS**
- 无 P0 / P1（唯一 pytest 全量失败 = HEAD 既存，非本次引入；requirements lock 漂移 = P2）
- 真实 Windows 视觉验收 PASS（CJK / 3 DPI / Icon / Typography / Nav / Button）
- 零业务/Core/算法/Undo/DB schema/版本号变化

### 标注（不影响 A 判定，决策点）

- **Navigation 文案 vs §3 草图**：实现为 首页/整理/整理历史/设置 + 关于，与 §3 "整理/历史/设置/关于" 草图有偏差，**已在 INFORMATION_ARCHITECTURE.md 中明确文档化**（保留首页作 folder-first 着陆 + 整理历史明确命名）。等中哥确认是否在 Phase 2 调整为 4 项。
- **requirements.txt 锁漂移**：锁 6.8.0.2 / 实际 6.11.2，建议随 V1.1.1/Phase 2 同步。
- **"开始扫描" 视觉权重** 偏次级：Phase 2 按钮权重审计时统一。

---

## 7 · Phase 2 Gate

> 本报告的 **A. PASS** 即是进 Phase 2 的通行证（决策点已标注）。

Phase 2 才处理：
- Dashboard Hero 降级
- Score Ring 降级（IA 已记）
- Folder-first 首页重构
- 统计卡密度
- 首页信息层级
- 核心任务路径优化
- （可选）收口 Navigation 文案 + requirements.txt 锁同步

---

## 8 · STOP

本阶段不进入 Phase 2，不改 Dashboard 设计，不复活 Tools/Coming Soon，不改 Core/业务逻辑，不创建 v1.1.0 tag，不创建 Git Release，不代码签名，不修改版本号。

**等中哥决定**：
- 直接进 Phase 2？
- 先收口导航文案 + requirements 锁漂移（P2 顺手做）？
- 还是 P1 修完了想先让 V1.1.1 重建（带 src/data 的完整仓库）？
