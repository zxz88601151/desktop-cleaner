# Desktop Cleaner 桌面文件整理助手

> 安全、本地、可撤销的 Windows 桌面文件整理工具。一键整理桌面 / 下载等杂乱文件夹，文件只移动、不删除、可还原。

**当前版本：1.1.1**（stable） · 平台：Windows · 完全本地运行 · 数据不上传

---

## 目录

- [一、项目简介](#一项目简介)
- [二、核心功能](#二核心功能)
- [三、快速上手](#三快速上手)
- [四、技术架构](#四技术架构)
- [五、数据与安全设计](#五数据与安全设计)
- [六、更新机制与发布链](#六更新机制与发布链)
- [七、构建与测试](#七构建与测试)
- [八、后期可扩展功能](#八后期可扩展功能)
- [九、文档索引](#九文档索引)
- [十、项目信息与作者](#十项目信息与作者)

---

## 一、项目简介

Desktop Cleaner（桌面文件整理助手）是一款面向 Windows 桌面的文件整理工具，解决「桌面 / 下载文件夹越来越乱、找不到文件」的日常痛点。

核心设计理念：

| 原则 | 说明 |
|---|---|
| **只移动，不删除** | 整理仅将文件移动到分类目录，绝不删除或覆盖任何文件 |
| **可撤销** | 每次整理均可一键还原，历史记录支持单独撤销 |
| **先预览，后执行** | 扫描后生成模拟报告，用户确认后才真正移动 |
| **完全本地** | 所有文件操作与数据存储均在本地，无任何上传 |
| **安全兜底** | 移动逐文件校验、冲突自动重命名、崩溃自动恢复 |

### 版本历史

| 版本 | 说明 |
|---|---|
| **1.1.1**（当前） | 新增「检查更新」入口，更新源迁移至公网 HTTPS；完善 About 页 |
| **1.1.0** | 统一版本、发布工程收口（Gitea Release） |
| **1.0.0** | 首个稳定版本 |

---

## 二、核心功能

### 2.1 智能整理（Organize）

- **两种整理模式**
  - **按类型**：将文件按扩展名归类（图片、文档、视频、音频、压缩包、代码、安装程序、其他 8 类）
  - **按日期**：按文件的最后修改月份归档（`2026-09` 等）
- **可选包含子文件夹**：决定是否递归整理目标目录下的子目录
- **自动排除**：跳过系统 / 隐藏文件，跳过已整理的输出目录，禁止整理应用自身数据目录
- **支持约 150 种扩展名规则**（`DEFAULT_RULES`），8 大类 + emoji 标识

### 2.2 扫描与预览

- 扫描后按类别展示：文件数量、总大小、常见扩展名、占比条形图
- 整理前生成**模拟报告**（要移动的文件清单与目标位置），确认后才执行

### 2.3 安全移动

- 逐文件校验源 / 目标路径
- 冲突自动重命名：`name (1).ext`、`name (2).ext`……
- **绝不覆盖、绝不删除**
- 整理完成后提供：一键还原、查看历史、再整理一次、查看失败明细

### 2.4 整理历史与撤销

- 时间线式历史记录（含相对时间）
- 单条历史可撤销，最近一次整理可一键还原
- 崩溃恢复：移动采用「两阶段落库」，应用启动时自动对账未完成操作

### 2.5 首页仪表盘（Dashboard）

- 问候语 + 电脑整洁度评分（环形进度）
- 统计卡片：已整理文件数、释放空间、整理次数
- 一键还原最近一次整理

### 2.6 自定义整理方案（Custom）

- 按类型 / 按日期两种自定义卡片，真实预设可直接使用
- 可扩展更多自定义规则

### 2.7 更多工具（Tools / Coming Soon）

内置功能注册中心（Feature Registry），已上线「文件整理」，另规划 10 个扩展工具（详见[第八章](#八后期可扩展功能)），界面自动随注册表更新。

### 2.8 主题

- 浅色 / 深色两套主题，全局即时切换

### 2.9 检查更新

- About 页与设置页提供「检查更新」入口
- 访问公网 HTTPS 更新源，获取 manifest 并与当前版本比较
- 状态明确区分：**已是最新 / 发现新版本 / 检查失败**（网络异常绝不被误报为"已是最新"）

---

## 三、快速上手

### 运行（已打包版本）

下载 `DesktopCleaner-1.1.1.exe`，双击运行，无需安装。

### 源码运行

```powershell
# 进入项目根目录（含 venv）
cd desktop-cleaner
.\venv\Scripts\python.exe main.py
```

### 使用流程

1. 打开应用，默认进入「智能整理」
2. 选择文件夹（桌面 / 下载……）→ 开始扫描
3. 查看分类预览 → 整理前查看模拟报告
4. 确认整理 → 完成后可一键还原

---

## 四、技术架构

```
main.py                   入口：高 DPI、初始化数据库、启动后台更新检查
│
├── src/core/             业务核心（纯逻辑，无 UI）
│   ├── scanner.py        扫描（按类型 / 按日期）
│   ├── classifier.py     扩展名 → 类别
│   ├── organizer.py      整理计划、模拟报告、安全移动、撤销
│   └── rules.py          分类规则 + 默认规则表
│
├── src/data/             数据层（SQLite）
│   ├── database.py       连接管理（WAL / busy_timeout）
│   ├── settings_repo.py  设置 KV
│   ├── history_repo.py   历史 + 统计
│   └── operation_repo.py 移动操作两阶段落库 + 启动对账
│
├── src/ui/               PySide6 界面
│   ├── app_shell.py      侧边栏 + 路由（5 页）
│   ├── pages/            首页 / 智能整理 / 自定义 / 历史 / 设置 / 更多工具
│   ├── about.py          About 页（作者信息 + 检查更新）
│   ├── features.py       功能注册中心（Feature Registry）
│   ├── coming_soon.py    Coming Soon 对话框
│   ├── preview_report.py 模拟报告
│   └── undo.py           撤销
│
├── src/update/           更新子系统
│   ├── constants.py      生产更新源 + URL 白名单 + 安全校验
│   ├── checker.py        manifest 拉取（fail-closed）
│   ├── version.py        语义版本比较
│   ├── decision.py       更新决策（none / normal / important / force）
│   ├── manifest.py       manifest 解析
│   ├── integrity.py      SHA-256 完整性原语（为自动更新预留）
│   ├── manager.py        后台更新检查（QThread + 节流）
│   └── update_dialog.py  发现新版本弹窗
│
└── src/utils/            工具（错误处理 / 格式化 / 日志 / 路径）
```

### 技术栈

| 项 | 值 |
|---|---|
| 语言 | Python 3.13.14 |
| GUI | PySide6 6.11.2 |
| 存储 | SQLite（WAL 模式） |
| 打包 | PyInstaller 6.22.2（one-file 单文件） |
| 测试 | pytest 9.1.1（47 项用例） |

---

## 五、数据与安全设计

### 5.1 数据存储

- SQLite 数据库：`WAL` 模式、`busy_timeout=5000ms`、`synchronous=NORMAL`
- 三张表：`settings`（设置）、`history`（整理历史）、`operations`（移动操作，FK 级联）
- 数据目录优先级：
  1. `DESKTOP_CLEANER_HOME` 环境变量（测试 / 隔离用）
  2. 打包运行时：`%APPDATA%\DesktopCleaner`
  3. 源码运行：项目根目录

### 5.2 文件安全

- 只移动、不删除、不覆盖
- 冲突自动重命名，绝不静默替换
- 移动前逐文件校验，失败可查看明细
- 两阶段落库 + 启动对账，断电 / 崩溃可恢复

### 5.3 网络安全（更新源）

- 仅允许 **HTTPS** + **Host 白名单**（`update.ycqinnan.cn`）
- 拒绝：`http://`、`localhost`、内网地址（`192.168.x.x` 等）、`file://`、任意其他公网域名
- 下载 URL 校验：HTTPS + 白名单 + 443 端口 + 无 userinfo
- manifest 校验：`product == DesktopCleaner`、语义版本合法，任何异常按「检查失败」处理（fail-closed）
- **不自动下载、不自动安装、不自动替换**，仅提供用户主动的下载入口

---

## 六、更新机制与发布链

### 6.1 更新源

- **生产更新源（manifest）**：`https://update.ycqinnan.cn/update/latest.json`
- **生产下载地址**：`https://update.ycqinnan.cn/releases/DesktopCleaner-1.1.1.exe`
- 支持 `DC_UPDATE_MANIFEST_URL` 环境变量覆盖（测试 / 隔离）
- 检查节流：24 小时；网络超时：8 秒；后台非阻塞检查

### 6.2 Manifest 契约

```json
{
  "schema_version": 1,
  "product": "DesktopCleaner",
  "latest_version": "1.1.1",
  "minimum_supported_version": "1.1.0",
  "release_channel": "stable",
  "download_url": "https://update.ycqinnan.cn/releases/DesktopCleaner-1.1.1.exe",
  "sha256": "22493096bd0ae9bcce4438b6b5eb48a089a178aa7245866f4392f60c7d7c18d6",
  "release_notes": ["..."],
  "published_at": "2026-09-03"
}
```

### 6.3 发布链（Source Separation）

```
内部 Gitea（开发 / 内部 Release）
        ↓ 受控发布同步
公网 Update Host（https://update.ycqinnan.cn）
        ├── /update/latest.json        （no-cache）
        └── /releases/*.exe            （immutable 长缓存）
        ↓
Desktop Cleaner 客户端
```

**发布顺序（铁律）**：构建 EXE → 计算 SHA256 → 校验 → 上传 EXE → 验证公网 200 → 验证公网 SHA256 → 发布 latest.json → 验证 → 端到端检查。**latest.json 永远不能先于对应 EXE 发布**。

### 6.4 公网 Host 安全基线

- HTTPS only（Let's Encrypt），HTTP 自动 301 到 HTTPS，TLS 1.2+
- `/releases/` 目录 403、无 autoindex
- 纯静态 GET：无上传 API、无 POST/PUT/DELETE、无脚本执行、无目录遍历
- manifest 变化（no-cache）、版本化 EXE 长缓存（`public, max-age=31536000, immutable`）

### 6.5 制品完整性

| 项 | 值 |
|---|---|
| 版本 | 1.1.1 |
| 制品 | `DesktopCleaner-1.1.1.exe` |
| 大小 | 39,287,338 B |
| SHA-256 | `22493096bd0ae9bcce4438b6b5eb48a089a178aa7245866f4392f60c7d7c18d6` |
| 架构 | x64 / Windows GUI |
| 签名 | 未签名（SmartScreen 声誉未建立，后续阶段处理） |

---

## 七、构建与测试

### 7.1 构建

```powershell
# 一键打包（安装依赖 + PyInstaller）
.\build.bat

# 或直接
pyinstaller build.spec
```

- 产物：`dist\DesktopCleaner.exe`（one-file 单文件）
- 版本化命名：发布时受控复制为 `DesktopCleaner-<version>.exe` 并校验哈希
- `build.spec` 已内联：name / one-file / windowed / hiddenimports / `assets/author.jpg` 资源 / 代码签名占位

### 7.2 发布校验

```powershell
python tools/release_validate.py            # 本地全量校验
python tools/release_validate.py --check-remote   # 额外校验公网制品
```

校验项：EXE 存在性 / 文件名一致性 / SHA256 一致性 / 版本一致性 / 下载制品 / 发布元数据。

### 7.3 测试

```powershell
$env:DESKTOP_CLEANER_HOME = "$env:TEMP\dc_test_home"   # 隔离数据目录
$env:QT_QPA_PLATFORM = "offscreen"                      # 无头测试
python -m pytest -q
```

**当前：47 passed**（覆盖核心整理、路径、安全、更新、UI、崩溃恢复、发布契约等）。

---

## 八、后期可扩展功能

本项目的扩展能力由 **功能注册中心（`src/ui/features.py`）** 统一管理。注册中心是产品能力的唯一事实来源，Tools 页与 Coming Soon 对话框均只读取该注册表，**界面不会硬编码任何功能名**。新增工具时，只需把对应条目的 `status` 从 `COMING_SOON` / `PLANNED` 翻转为 `AVAILABLE` 并实现其业务模块，UI 自动更新，无需改导航与落地页。

### 8.1 已规划功能路线图

| 功能 | 状态 | 分类 | 说明 |
|---|---|---|---|
| 文件整理 | ✅ 已上线 | 核心 | 当前核心工具 |
| 护眼模式 | 🔜 即将上线 | 舒适 | 降低屏幕刺激，夜间更舒适 |
| 快速锁屏 | 🔜 即将上线 | 安全 | 一键锁定电脑 |
| 重复文件查找 | 🔜 即将上线 | 存储 | 发现重复文件，释放磁盘空间 |
| 大文件分析 | 🔜 即将上线 | 存储 | 定位占用空间较大的文件 |
| 空文件夹清理 | 🔜 即将上线 | 存储 | 发现长期未使用的空文件夹 |
| 批量重命名 | 🔜 即将上线 | 效率 | 按统一规则批量改名 |
| 快速搜索 | 🗓 规划中 | 效率 | 更快找到电脑中的文件与文件夹 |
| 文件夹分析 | 🗓 规划中 | 存储 | 查看文件数量 / 类型 / 大小 / 占用 |
| 定时整理 | 🗓 规划中 | 自动化 | 按时间计划自动整理指定文件夹 |
| 开机整理 | 🗓 规划中 | 自动化 | 开机后自动检查指定目录 |

### 8.2 架构演进方向

| 方向 | 现状 | 后续目标 |
|---|---|---|
| **自动更新（Option A）** | `update/integrity.py` 已实现 SHA-256 校验原语（HTTPS → SHA-256 → Authenticode 链路就绪），当前为「仅检查不下载」 | 发布后启用「下载 + 校验 + 替换」完整自动更新 |
| **代码签名** | 未签名，`build.bat` / `build.spec` 已预留 `signtool` 签名位（`CERT_PFX` / `CERT_PWD`） | 引入代码签名证书，建立 SmartScreen 声誉，消除未签名警告 |
| **更新检查缺陷修复** | 已知：设置页离线时可能误报"已是最新"（与 About 页的 fail-closed 语义不一致） | 独立阶段修复，统一错误语义 |
| **分类规则扩展** | 内置 8 类约 150 扩展名规则 | 支持用户自定义分类规则与规则可视化编辑 |
| **整理策略增强** | 按类型 / 按日期 | 支持自定义命名模板、目标目录规则、更多整理模式 |
| **数据层演进** | SQLite WAL 本地存储 | 导出整理报告（HTML / CSV）、更多统计维度 |

### 8.3 扩展开发约定

1. **新增功能**：在 `features.py` 增加 `FeatureDefinition`，实现对应业务模块，翻转 `status` 即可上线，UI 自动展示。
2. **安全底线**：任何涉及文件删除 / 覆盖 / 网络下载的功能，必须沿用「先预览、可撤销、fail-closed、白名单校验」的安全模型。
3. **阶段治理**：遵循项目的逐阶段授权流程（设计 → 审计 → 受控实施 → 验证 → 发布），不跳阶段。

---

## 九、文档索引

项目文档已整理归档，根目录仅保留本 README 作为唯一门面：

| 位置 | 内容 |
|---|---|
| `README.md`（本文件） | 项目介绍、功能、架构、发布链、扩展路线图 |
| `docs/` | 当前有效的工程文档（依赖基线、阶段收口报告等） |
| `docs/archive/` | 历史过程报告归档（Phase 系列、UI-1.1/1.2/1.3 系列、审计 / 冻结 / 计划等，保留 Git 历史可回溯） |
| `docs/ui-1.3-phase1*` | UI 阶段截图（多 DPI） |
| `design/` | 设计原型与截图 |

> 说明：历史过程性报告统一归档至 `docs/archive/`，避免大量 .md 直接堆在项目根目录影响浏览；如需查阅历史报告，进入该目录即可。

---

## 十、项目信息与作者

- **产品**：Desktop Cleaner 桌面文件整理助手
- **版本**：1.1.1
- **作者**：张兴中
- **微信**：zxzjxx007
- **版权**：© 中哥  All Rights Reserved
- **源码托管**：内部 Gitea（开发 / 内部发布）
- **公网更新**：https://update.ycqinnan.cn
