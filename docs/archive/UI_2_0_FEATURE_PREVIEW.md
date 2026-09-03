# UI-2.0 — Feature Preview / Coming Soon Architecture

> 阶段定位：在不破坏现有产品与 UI Design System 的前提下，建立「未来功能展示 / Coming Soon」体系。
> 本阶段**不实现任何未来功能的业务逻辑**，只落地：Feature Registry + Tools Page + Coming Soon Dialog + 导航入口。
> 执行模式：READ → AUDIT → DESIGN → MINIMAL IMPLEMENTATION → TEST → STOP

---

## 1. 功能展示架构

```
Desktop Cleaner（当前产品：文件整理 / 扫描 / 预览 / 安全整理 / 撤销）
│
├─ 侧边导航（Sidebar）
│   首页 · 智能整理 · 整理历史 · [更多工具] · 设置
│                                    └─ 新增入口（Tertiary 视觉权重，不抢核心 CTA）
│
├─ 首页（Dashboard）
│   第一焦点：选择文件夹 → 开始扫描（不变）
│   轻量入口：发现更多工具 →（Tertiary 按钮，导航到 tools 页）
│
└─ 更多工具（ToolsPage）
    读取 Feature Registry → 渲染 10 张「即将上线 / 规划中」卡片
    点击卡片 → ComingSoonDialog（统一弹窗，无业务动作）
```

设计目标达成：
- 首页核心流程（扫描 / 预览 / 整理 / 撤销）视觉焦点**零变化**；
- 未来功能只以「产品预告」形态出现，**不伪装成已完成功能**；
- 所有未来功能元数据**唯一来源**是 `features.py`，页面/弹窗不硬编码。

---

## 2. Feature Registry

新增 `src/ui/features.py`（唯一事实来源，无 DB、无 core/data 依赖）。

- `FeatureStatus`：仅 3 态 —— `AVAILABLE` / `COMING_SOON` / `PLANNED`
  - 文案映射：`已上线` / `即将上线` / `规划中`
  - **禁止**虚假发布日期、虚假进度百分比。
- `FeatureDefinition`（`@dataclass`）：`key / name / icon / description / category / status / enabled / coming_soon / planned_version` + `status_label` 属性。
- `FEATURES`：当前 11 条
  - 1 × `AVAILABLE`：`FILE_CLEANER`（文件整理，当前核心能力）
  - 6 × `COMING_SOON`（护眼 / 锁屏 / 重复文件 / 大文件 / 空文件夹 / 批量重命名）
  - 4 × `PLANNED`（快速搜索 / 文件夹分析 / 定时整理 / 开机整理）
- 辅助：`get_features(include_available=False)` 默认排除 AVAILABLE（Tools 页只展示未来功能）；`get_feature(key)`。

> 未来真正开发某功能时：把该条的 `status` 从 `COMING_SOON`/`PLANNED` 改为 `AVAILABLE`，UI 自动切换为「已上线」，无需改导航或落地页。

---

## 3. Tools Page（更多工具）

新增 `src/ui/pages/tools_page.py`：

- `ToolCard(QFrame)`：正常显示、可点击、完整文字、统一 Icon、右上角状态 Badge。
  - 顶部：Icon + 状态 Badge（`tool-badge[state="coming|planned"]`）
  - 中部：功能名（`tool-name`）+ 描述（`tool-desc`，自动换行）
  - 底部：`了解功能 →`（`ghost-link` 纯文本提示，非按钮）
  - 点击卡片（`mousePressEvent`）→ 发射 `clicked(feature)` → 打开 `ComingSoonDialog`
- `ToolsPage(QWidget)`：标题「更多工具」+ 副标题「正在持续增加更多实用功能」+ 滚动卡片网格（2 列）。
  - `on_enter()` 留空实现（Registry 静态，无需刷新）。
- **关键设计**：卡片**不灰掉、不禁用、不被挤压**，看起来是「正常可点」的预告，而非 Bug。

---

## 4. Coming Soon Dialog

新增 `src/ui/coming_soon.py`：`ComingSoonDialog(QDialog)`

- 内容：大 Icon → 功能名（dialog-title）→ 状态 Badge → 描述 + 一句话「这个功能正在开发中，我们会在后续版本中加入。」
- 底部：单个 **Ghost**「返回」按钮（无「立即使用 / 开始 / 执行」）。
- `setModal(True)`；Enter / Esc / 窗口 X 均 `reject` 关闭，**绝不触发任何业务操作**。
- 复用既有 `dialog-title` / `dialog-body` / `tool-badge` token，与 Preview/Undo/About 视觉一致。

---

## 5. 当前功能状态

| 功能 | 状态 | 入口 |
|---|---|---|
| 文件整理（核心） | 已上线 | 首页 / 智能整理 |
| 护眼模式 | 即将上线 | 更多工具 |
| 快速锁屏 | 即将上线 | 更多工具 |
| 重复文件查找 | 即将上线 | 更多工具 |
| 大文件分析 | 即将上线 | 更多工具 |
| 空文件夹清理 | 即将上线 | 更多工具 |
| 批量重命名 | 即将上线 | 更多工具 |
| 快速搜索 | 规划中 | 更多工具 |
| 文件夹分析 | 规划中 | 更多工具 |
| 定时整理 | 规划中 | 更多工具 |
| 开机整理 | 规划中 | 更多工具 |

---

## 6. UI 交互

- 双按钮 Dialog 统一规则：取消/返回 = **Ghost 左**，确认/开始/还原 = **Primary/Undo 右**（延续 UI-1.2）。
- Coming Soon 单按钮 = Ghost「返回」，居中右对齐。
- 首页「发现更多工具」= **Tertiary**，不抢「开始扫描」Primary CTA。
- 侧边栏「更多工具」= 普通导航项（icon + 文字），与首页/整理/历史/设置同级。
- 所有新 Dialog/弹窗均为 modal，打开期间主页面不可误操作。
- Enter/Esc/X 安全：Coming Soon 三种关闭方式均为 `reject`，不会误触任何强操作。

---

## 7. Button System 复用情况

严格复用 UI-1.2 冻结的 Button System，**未新增任何 Variant**：

| 用途 | 复用 Variant |
|---|---|
| 首页「发现更多工具」 | `tertiary` |
| 侧边栏「更多工具」导航项 | 现有 `nav-item` |
| Coming Soon「返回」 | `ghost` |
| 卡片底部「了解功能 →」 | 纯文本 `ghost-link`（非按钮，复用配色） |

未使用 `primary` / `secondary` / `danger` / `undo-cta` 于任何未来功能（避免暗示「可用」）。

---

## 8. 未来扩展方式

新增一个工具只需要 4 步：
1. 在 `features.py` 的 `FEATURES` 增加一条定义（name/icon/description/category/status）；
2. Tools Page **自动**显示该卡片（无需改页面代码）；
3. 实现对应业务模块（core / worker / 数据层，按需新建，不碰现有整理逻辑）；
4. 状态从 `COMING_SOON` → `AVAILABLE`，UI 自动切为「已上线」。

> 已为未来功能预埋安全分级提示（见风险章节）：信息型 / 可逆 / 不可逆 / 系统级，届时由各模块单独做 OS Capability Detection，不支持则提示而非崩溃。

---

## 9. Windows 兼容策略

- 目标平台 Windows（10 / 11 为主，尽量兼容 8 / XP 界面观感）。
- 本阶段只做 UI，**不调用任何 Windows API**；未来功能（锁屏/定时/开机）真正开发时各自做 `OS Capability Detection`：
  - `if supported: enable else show_unsupported`，直接优雅降级，不崩溃。
- 锁屏等系统级能力**必须调用 Windows 标准能力**（如锁屏 API），不自建密码体系。
- Dialog 尺寸用 `setMinimumWidth` + 弹性布局，不固定死，兼容 100% / 125% / 150% DPI（沿用 UI-1.2 DPI 策略）。

---

## 10. 测试结果

| 测试 | 结果 |
|---|---|
| `compileall src main.py` | PASS |
| `test_core` | PASS |
| `test_security` | PASS |
| `test_reliability` | PASS |
| `test_windows_paths` | PASS |
| `test_p2_coverage` | PASS |
| `test_appshell` | PASS（见风险①：对齐一处 stale 断言） |
| `test_dashboard` | PASS |
| `test_first_launch` | PASS |
| `test_phase5_e2e` | PASS |
| `test_preview` | PASS |
| `test_theme` | PASS |
| headless 渲染校验（Tools 页 10 卡 / ComingSoon modal+Ghost 返回 / Sidebar 含「更多工具」/ 首页入口 tertiary / Light·Dark 解析） | PASS |

---

## 11. 风险

1. **测试对齐（已修复，非产品缺陷）**：`test_appshell.py` 原断言检查 `undo-done` 对象名，但 UI-1.2.2（已批准）已将整理完成页「一键还原」按钮重命名为 `undo-cta`。本次将该测试断言对齐为 `undo-cta`，使「已有测试全 PASS」成立。仅改测试引用，未改 undo 业务逻辑。
2. **未来功能安全分级**（已记录，待实现时落实）：重复文件/大文件/空文件夹第一阶段只扫描不删；批量重命名必须预览+撤销；定时/开机整理必须可关闭/禁用。本阶段仅 UI，不涉及。
3. **卡片网格固定 2 列**：窄屏（最小窗 900px）下 2 列足够；若未来功能远超 10 个，可考虑响应式列数（非当前阻塞项）。

---

## 12. 下一阶段建议

- 当前产品保持「完整、成熟、专业」；未来功能以预告形态存在，用户感知 = 「现在就好用，以后更强」。
- 后续可进入 **UI-1.3 Design System**（统一 Card / Typography / Spacing / Empty / Loading / Error / Toast / Progress / List / Badge / Status），再进入 **UI-2 Tools Hub 实质化**（当某功能真正开发时，从 Registry 翻状态即可）。
- **本阶段 STOP**：未实现任何未来功能业务逻辑，未改 core/data/scanner/organizer/undo/worker/DB。

---

## 修改文件清单

| 文件 | 类型 | 说明 |
|---|---|---|
| `src/ui/features.py` | 新增 | Feature Registry（唯一事实来源） |
| `src/ui/coming_soon.py` | 新增 | 统一 Coming Soon Dialog（Ghost 返回，modal，无业务） |
| `src/ui/pages/tools_page.py` | 新增 | 更多工具页（卡片网格，点击开 Dialog） |
| `src/ui/widgets/sidebar.py` | 改 | `_NAV` 增加「更多工具」导航项 |
| `src/ui/app_shell.py` | 改 | 导入 ToolsPage；`_TITLES`/`_pages` 注册 tools |
| `src/ui/pages/dashboard_page.py` | 改 | 首页增加 Tertiary「发现更多工具」入口 |
| `src/ui/theme/themes.py` | 改 | 增加 `#tool-card`/`#tool-icon`/`#tool-name`/`#tool-desc`/`#tool-badge`/`#coming-soon` 样式 |
| `build.spec` | 改 | hiddenimports 增加 `ui.pages.tools_page` / `ui.coming_soon` / `ui.features` |
| `tests/test_appshell.py` | 改 | 对齐 stale 断言 `undo-done` → `undo-cta`（非产品逻辑改动） |
