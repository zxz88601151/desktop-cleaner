# Desktop Cleaner — 项目审计报告（Current Project State）

> 审计日期：2026-08-31（只读审计，未改动任何产品代码）
> 审计方式：项目考古（代码 + 测试 + Git + 构建产物 + 发布端点实证核查）

---

## 0. 结论速览

| 维度 | 结论 |
|---|---|
| 产品代码质量 | **B（良好）** — 分层清晰、安全设计扎实，无 P0/P1 产品代码缺陷 |
| 测试状态 | **部分通过** — 29/30 PASS；1 项失败为测试隔离缺陷（非产品 bug） |
| 发布就绪度 | **B. READY WITH CONDITIONS** — 无代码级阻断，但有 3 个一致性问题需处理 |
| 总评 | **B-（可发布，但先处理下述 P1）** |

**3 个 P1 项（发布工程层，非产品代码）：**

1. **P1-1 更新系统渠道与真实发布地不一致**：`update/constants.py` 的 manifest URL 指向 `raw.githubusercontent.com/zxz88601151/desktop-cleaner/main/update_manifest.json`（实测 HTTP 404 / 网络不可达），而真实发布在局域网 Gitea（`192.168.3.200:3000/zxzjxx/desktop-cleaner`，manifest 实测 HTTP 200）。**线上 EXE 的"检查更新"永远静默失败**——但按设计它不阻塞主功能（非核心依赖，失败静默），故定性 P1 而非 P0。
2. **P1-2 测试套件全量运行 1 项失败**：`tests/test_p2_coverage.py::test_legacy_db_wal_upgrade` 断言 `cnt==1` 失败。根因：`database.py` 的 `DB_PATH` 在模块首次 import 时固定，而各测试文件在模块级各自设置 `DESKTOP_CLEANER_HOME`，pytest 全量收集时先导入的测试文件已缓存模块，后导入文件的 env 覆盖失效 → DB 落到别的测试的临时目录 → `history` 表有脏数据。单独运行该文件全通过（已验证）。**测试基础设施问题，产品代码无 bug。**
3. **P1-3 发布产物与 manifest/SHA256SUMS 脱节**：`RELEASE_MANIFEST.md` 记录 artifact 为 `DesktopCleaner-1.1.0.exe`（39,368,407 B / SHA `0fd68615...`），`SHA256SUMS.txt` 同记录；但 `dist/` 实际只有 `DesktopCleaner.exe`（39,377,965 B / SHA `f2c7dcd1...`，构建于 08-28 21:41）。文件名、大小、哈希全部不一致——**manifest 与校验和文件描述的是旧产物，当前 EXE 无人背书**。

---

## 1. 技术栈与环境（实测证据）

| 项 | Declared | Actual（实测命令） | 一致 |
|---|---|---|---|
| Python | 3.13.14 | 3.13.14（`venv/Scripts/python.exe --version`） | ✅ |
| PySide6 | 6.11.2 | 6.11.2（`import PySide6`） | ✅ |
| PyInstaller | 6.22.2 | 6.22.2（`-m PyInstaller --version`） | ✅ |
| 架构 | — | AMD64（`platform.machine()`） | ✅ |
| OS | Windows 10/11 | Windows（构建环境） | ✅ |
| GUI 框架 | Qt 6 Widgets（Fusion 风格） | 同 | ✅ |
| 数据层 | SQLite（WAL + busy_timeout） | 同 | ✅ |
| 更新系统 | 纯 stdlib（urllib + ssl） | 同 | ✅ |

依赖基线收口（Phase 1.5）已生效：`requirements.txt` 精确钉版，无 `latest`/`>=`，Declared == Actual == Tested。

## 2. 架构与模块职责

```
main.py                    入口：init_db → reconcile_pending(P0-1 崩溃恢复) → AppShell → 后台更新检查
src/
├── core/                  ⚙️ 业务纯逻辑（无 Qt/DB 依赖）
│   ├── classifier.py      扩展名 → 分类键（unknown → others）
│   ├── rules.py           分类规则表（8 大类 + 表情）＋ 排除目录/日期目录识别
│   ├── scanner.py         扫描 + 分组预览（隐藏/系统文件跳过、防扫自身数据目录）
│   └── organizer.py       移动计划 + 执行 + 校验 + 撤销（防覆盖、长路径）
├── data/                  🗄️ 持久层
│   ├── database.py        SQLite 连接（WAL/synchronous=NORMAL/busy_timeout）＋ schema
│   ├── settings_repo.py   KV 设置表
│   ├── history_repo.py    整理历史
│   └── operation_repo.py  移动记录 + pending 恢复（P0-1）+ undo 结算（P0-2）
├── ui/                    🎨 Qt Widgets 界面（AppShell 壳 + Sidebar + 5 页面 + 主题系统）
│   ├── app_shell.py       240px Sidebar + QStackedWidget 路由壳
│   ├── pages/             首页/整理/整理方案/历史/设置 + tools(Coming Soon 预览)
│   ├── state/worker.py    后台任务线程（业务层冻结，仅包装）
│   ├── theme/             设计 token + 双主题（光/暗）
│   └── undo.py            撤销对话框
├── update/                🔄 更新系统（Option B：仅检查，不自动替换 EXE）
│   ├── checker.py         HTTPS manifest 拉取（纯 stdlib，失败静默 → None）
│   ├── decision.py        四级决策 NONE/NORMAL/IMPORTANT/FORCE
│   ├── manager.py         QThread 非阻塞 + 24h 节流（settings 持久化）
│   ├── integrity.py       SHA-256 原语（为 Option A 预留）
│   └── update_dialog.py   更新提示框（新版本 + 发布说明 + 跳转下载页）
└── utils/                 路径长前缀、日志、错误消息、格式化
```

## 3. 代码质量评估（亮点）

- **安全设计扎实**：文件只移动不删除；目标冲突重命名 `(1)` 而非覆盖；移动后校验（target 存在 && source 消失）才算成功；`win_long` 长路径前缀（≥240 字符才加，短路径不受影响）；隐藏文件/系统文件（desktop.ini/thumbs.db）跳过；禁止整理应用自身数据目录；启动时 pending 校准（崩溃恢复 P0-1）。
- **分层干净**：core 无 Qt/DB 依赖，update 网络层无 Qt，可独立单测；UI 壳不直接摸业务，通过 worker 线程包装。
- **更新系统设计正确**：FORCE 判定 `current < minimum_supported_version` 边界正确（测试含 boundary case）；版本比较为数值元组（1.1.9 < 1.1.10 正确）；24h 节流；失败静默不阻塞主流程。
- **诚实的占位**：Tools 页明确为 Coming Soon 预览（`coming_soon.py` 声明"不执行任何业务动作"），非 Fake Implementation。
- **日志/错误处理**：单行结构化日志（时间/级别/模块/消息）、Worker 异常 → 全 traceback 进日志 + UI 显示友好文案。

## 4. 测试（实测运行结果）

`pytest tests/ -q`（2026-08-31 实测）：**29 passed, 1 failed**

| 套件 | 覆盖 | 结果 |
|---|---|---|
| test_core / test_windows_paths | 分类、扫描、长路径 | ✅ |
| test_phase5_e2e / test_combined_path_v11 | 15 场景 E2E、中文+空格组合路径 | ✅ |
| test_reliability / test_security / test_dashboard | 可靠性、安全、仪表盘 | ✅ |
| test_theme / test_appshell / test_first_launch | 主题、壳、首启 | ✅ |
| test_update | 版本比较/manifest/决策/完整性/manager（mock 网络） | ✅ |
| test_p2_coverage | 缺失源文件、legacy DB→WAL、崩溃恢复、日志格式 | ❌ T2 失败（隔离缺陷） |

> T2 失败详情见结论 P1-2。单独运行 `python tests/test_p2_coverage.py` → **ALL PASSED**，证明是 pytest 全量收集顺序导致的测试间环境污染，非业务逻辑问题。

## 5. Git 状态

- 分支 `main`，工作树干净，HEAD = `3cb64d1`（chore(deps): align dependency baseline + Phase 1.5 closure）
- 提交历史 8 条，最近 3 条为 UI-1.3 Phase 1.5 收口
- remote：`origin` = GitHub（zxz88601151/desktop-cleaner）、`gitea` = 局域网 192.168.3.200:3000/zxzjxx/desktop-cleaner
- 本地 main 与 gitea/main 同 commit（`git ls-remote gitea` 确认 3cb64d1 == HEAD），gitea 有 `v1.1.0` tag；本地提示 `gitea/main: gone`（upstream 跟踪丢失，非内容差异）
- `.gitignore` 覆盖 build/dist/data/*.db/*.log/pytest 缓存/临时沙箱 ✅（仓库卫生良好）

## 6. 构建产物与发布工程

| 项 | 状态 |
|---|---|
| dist/DesktopCleaner.exe | 存在，39,377,965 B，SHA `f2c7dcd1...`（实测 certutil） |
| 代码签名 | **NOT SIGNED**（signtool 10.0.26100.0 存在，仓库无证书；`signtool verify` → Number of errors: 1 / No signature found） |
| SmartScreen | NOT ESTABLISHED（无 EV 证书、无信誉史） |
| Win32 版本资源（P2-a） | **未嵌入**（EXE 内无 VS_VERSION_INFO/ProductVersion/FileVersion 字符串） |
| 应用图标（P2-b） | **未嵌入**（build.spec 无 icon 配置） |
| PyInstaller 标志 | 确认（PyInstaller/_MEIPASS/python3 字符串均在） |
| 更新 manifest（Gitea） | HTTP 200，内容与本地 update_manifest.json 一致 |
| 更新 manifest（GitHub） | HTTP 404 / 不可达 ← **与代码配置不符（P1-1）** |
| release 页（GitHub） | 网络不可达；真实发布在 Gitea |

## 7. 已完成 / 未完成

**已完成（V1.1.0 范围）**：核心整理（类型/日期两模式）、预览报告、撤销、整理历史、自定义规则、设置页、双主题、仪表盘、多页面壳、Coming Soon 预览页、更新系统（Option B 检查版）、崩溃恢复、长路径支持、依赖基线收口、13 套功能测试。

**未完成 / 待办**：
- P2-a Win32 版本资源嵌入
- P2-b 应用图标
- P2-c 代码签名 + SmartScreen（需外部证书）
- P2-d 安装器（InnoSetup/NSIS）
- P2-e 版权/设备指纹 token（产品决策）
- P2-f XP/Win8 明确不支持横幅
- EB-1 代码签名证书（外部阻断）
- EB-2 SmartScreen 信誉（跟随 EB-1 + 下载量）

## 8. P0 / P1 / P2 分级

**P0（无）**：未发现数据丢失、崩溃、安全漏洞等发布阻断级缺陷。

**P1（3 项，均为发布工程层，非产品代码）**：
1. 更新渠道 URL 指向不可达端点（GitHub 404），真实发布在 Gitea → 线上更新检查失效。**建议**：`constants.py` 的 `UPDATE_MANIFEST_URL`/`DOWNLOAD_PAGE_URL` 改为 Gitea 实际地址，或在 Gitea 上补 GitHub 镜像。
2. 测试套件全量运行 1 项失败（测试隔离缺陷）。**建议**：测试文件内不用模块级 env 覆盖共享模块，改用 fixture 级 `monkeypatch` + 重置 `database.DB_PATH`，或为 `database.py` 增加 `configure(home)` 显式重载接口。
3. 发布产物与 RELEASE_MANIFEST/SHA256SUMS 脱节。**建议**：要么重签 manifest 记录当前 EXE 的哈希/文件名，要么用 manifest 描述的产物重新构建并核对哈希，二选一后让三方一致。

**P2（记录，不阻塞）**：版本资源、图标、签名、安装器、指纹 token、XP/Win8 横幅、`update_manifest.json` 中 `sha256` 字段为空（Option A 启用后需填充）。

## 9. 技术债与下阶段建议

1. **修复更新渠道一致性（P1-1）**是发布下一版前的必修项——否则用户永远不会收到更新提示。
2. **建立发布校验脚本**：构建后自动比对 manifest 记录的哈希与实际产物，防止 P1-3 再现。
3. **测试隔离改造（P1-2）**：为 `database.py` 增加显式 `configure(home_dir)` API，测试统一走 fixture，消除模块级 env 依赖。
4. Option A（自动下载+校验+自替换）：`integrity.py` 的 SHA-256 原语已就绪，但需先解决 EB-1 证书与 manifest `sha256` 填充。
5. 签名链路：build.bat 已预留 `CERT_PFX`/`CERT_PWD` 环境变量签名的注释块（无密钥入库，模式正确），拿到证书即可启用。
6. 若面向非局域网用户分发，需将发布渠道从 Gitea 迁移到 GitHub Releases（当前 GitHub 侧仓库不可达，需确认是否创建/推送）。

## 10. 审计方法与证据

- 环境版本：实测 venv 内 python/PySide6/PyInstaller 版本命令
- 测试：`pytest tests/ -q` 全量 + 单独复跑失败套件对照
- 产物：certutil SHA-256、signtool verify、EXE 内版本资源/打包标志字符串扫描
- 端点：curl 实测 GitHub raw / releases / Gitea raw 状态码
- Git：status/log/branch -vv/ls-remote 交叉核对
- 全部为只读操作，未修改任何源文件
