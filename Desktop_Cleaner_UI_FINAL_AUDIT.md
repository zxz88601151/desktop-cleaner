# 《Desktop Cleaner UI FINAL AUDIT》

> 阶段：**UI-0 · READ ONLY UI AUDIT（只读审查，零代码改动）**
> 范围：V1.0 最终 UI 审查 + 未来功能架构预留
> 审查日期：2026-08-28
> 结论前提：本审计报告**不修改任何代码**，仅描述现状、风险与改造建议。后续 UI-1…UI-10 阶段依据本报告落地。

---

## 0. 重要前置澄清（与需求文档的结构差异）

需求文档假设项目存在 `main_window.py` / `styles.py`。**实际不存在。** 真实结构如下：

| 需求文档假设 | 真实实现 |
|---|---|
| `main_window.py` | `src/ui/app_shell.py`（`AppShell` = Sidebar + QStackedWidget 路由） |
| `styles.py` | `src/ui/theme/themes.py`（真实 token 化 QSS）+ 三个**转发 shim**：`src/ui/themes.py`、`src/ui/theme_manager.py`、`src/ui/styles.py` |
| 未提及 | `src/main.py`（入口，已启用 High-DPI 属性） |

三个 shim 被 **15+ 真实模块**引用（`app_shell`、`dashboard`、`widgets/controls`、`widgets/score_ring`、`ui/undo`、`pages/*` 等），且在 `build.spec` 的 `hiddenimports` 中显式声明。**它们不能删除**，只能在未来阶段统一重指向 `ui.theme.*` 后再清理。

真实主题系统已是 token 化：`LIGHT`/`DARK` 调色板 + 单一 `QSS_TEMPLATE`（`{token}` 占位符），经 `build_stylesheet()` 渲染。这是好的基础，无需推翻。

---

## A. 当前 UI 已经做得好的地方

1. **Token 化双主题系统已就位**（`ui/theme/themes.py`）：颜色 / 圆角 / 字体集中为 token，`light`/`dark` 一套模板渲染，无 CSS 变量 hack。这是 V1.0 设计系统的核心地基。
2. **按钮层级已初步成型**：QSS 已定义 `#primary` / `#secondary` / `#ghost` / `#danger` / `#icon` / `#link`，首页"开始扫描"用 primary、浏览用 secondary，符合 ONE PRIMARY ACTION 原则。
3. **首页 Hero 已收敛到"选文件夹 → 扫描 → 预览"**：`dashboard_page.py` 已实现路径输入框 + 选择/扫描按钮 + `start_scan` Signal 直连 Organize 流程（P0 已完成），整洁度环被降级为角落辅助卡片。
4. **整理页"扫描→预览→确认→执行"四步安全门完整**：`organize_page.py` 先真实扫描、`PreviewReportDialog` 二次确认、`_task_organize` 严格 4 步（建记录→pending→移动+校验→更新状态），业务零改动。
5. **预览卡片含扩展名提示**：`_render_preview` 用 `_EXT_BY_LABEL` 反向映射展示"常见扩展名"，降低用户陌生感。
6. **完成页分类统计已从 `result.items` 派生**（P2-6）：`🖼️ 图片 2 · 📄 文档 1 …`，无 `by_category` 假设，数据层未触碰。
7. **历史页相对时间 + 源路径**：`history_page.py` 的 `_relative_time` + `source_path` 已显示，撤销按钮已从 danger 改为 secondary（P1-4）。
8. **分类名已做 internal key / display name 分离**（`core/rules.py`）：`CATEGORY_NAMES`（key→中文）、`DEFAULT_RULES`（ext→key）、`category_display()`、`category_emoji()`，未来扩展分类无需改 UI 文案硬编码。
9. **首启动欢迎 + 关于页** 文案克制、安全卖点清晰（本地运行 / 只移动不删除 / 可撤销）。
10. **高 DPI 属性已开启**（`main.py` 第 33-34 行），且 `ScoreRing`/`ToggleSwitch` 用 `QPainter` 绘制（按 DPR 自动清晰）。
11. **自定义控件组件化雏形已有**：`ui/widgets/controls.py`（`ToggleSwitch`/`Segmented`）、`ui/widgets/score_ring.py`、`ui/widgets/sidebar.py` 已抽离，符合"组件提取到 `src/ui/components/`"方向。

---

## B. 当前 UI 必须修改的地方（Must-Fix）

| # | 位置 | 问题 | 建议 |
|---|---|---|---|
| B1 | `src/ui/about.py:59` | 版权文案为 `f"{AUTHOR} · All Rights Reserved"` → `"© 中哥 · All Rights Reserved"`，与需求要求的**逐字原文 `© 中哥  All Rights Reserved`（中间两空格、无 `·`）** 不符 | 新增常量 `COPYRIGHT_TEXT = "© 中哥  All Rights Reserved"` 并**逐字使用**；`version.AUTHOR` 仅保留 `"© 中哥"` |
| B2 | `src/ui/theme/themes.py` `#badge` | `color: #FFFFFF` 硬编码；深色主题下 accent=`#818CF8`（浅紫），白字对比度差 | 改为 token `{on_accent}` |
| B3 | `src/ui/dashboard.py` `StatCard` | `refresh_shadows()` 定义了但从不在主题切换时调用（`DashboardPage._on_theme` 只 `self._ring.update()`）→ 切深色后卡片阴影颜色仍是浅色值 | 在 `DashboardPage._on_theme` 中调用 `self._stats.refresh_shadows()` |
| B4 | `src/ui/widgets/sidebar.py` `_NAV` + `app_shell._TITLES` | 导航缺 **"更多工具"**（未来功能 Hub）且 **"关于"** 仅为顶栏按钮，不符合需求导航结构 `首页/文件整理/更多工具/历史/设置/关于` | 新增 `tools` 页（Feature Registry Hub）；关于可保留顶栏入口或并入导航（见 F） |
| B5 | `src/main.py:33-34` | `Qt.AA_EnableHighDpiScaling` / `Qt.AA_UseHighDpiPixmaps` 在 PySide6 6.8 已**废弃**，运行时打印 warning 且 PMv2 DPI 感知未声明 | 改用 manifest 或 `ctypes` 在 `QApplication` 前设 `PROCESS_PER_MONITOR_DPI_AWARE`/`DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2`，并移除废弃属性（见 K） |
| B6 | `src/ui/theme/themes.py` 缺失 `#tertiary` | 需求按钮体系要求 **Primary/Secondary/Tertiary/Danger/Ghost/Disabled** 六档，当前 QSS 无 `tertiary` | 新增 `#tertiary` token 样式 |
| B7 | `src/ui/theme/themes.py` | 间距（8/10/12/14/16/18/22/24/28）散落在各页面 `setSpacing/setContentsMargins`，未集中为 4–40 间距 token | 在 `themes.py` 增加 `SPACING` token 字典并引用（见 J） |
| B8 | `src/ui/pages/organize_page.py:46-48` | `_EXT_BY_LABEL` 反向映射在页面模块级重复计算，未集中 | 收敛到 `core/rules.py` 或新 `features.py`，避免未来多页面各自重算 |

---

## C. 建议删除的 UI（Delete）

1. **`custom` 独立导航项已从侧栏移除，但 `CustomPage` 对象仍注册在 `AppShell._pages`**（`app_shell.py:74`）。当前不可达（无入口）。建议：在 UI-10 清理阶段，要么提供真实入口，要么彻底移出 `_pages` 并同步修改 `tests/test_appshell.py:67-69`（该测试**断言 `custom` 页存在/可路由**，是删除的硬约束，必须先改测试）。
2. **三个 legacy shim 的"双路径"历史包袱**（`src/ui/themes.py`、`src/ui/theme_manager.py`、`src/ui/styles.py`）：逻辑上已死，仅因 15+ 模块引用而保留。建议：未来阶段把所有 `from ui.themes` / `from ui.theme_manager` 改为 `from ui.theme.themes` / `from ui.theme.theme_manager`，再删除 shim 与 `build.spec` 中对应 hiddenimports。**不在本只读阶段执行。**
3. **`#score-v`（56px）token 已定义但未被使用**（首页用 `score-v-sm`）。可删除冗余 token，或在需要时复用。

---

## D. 建议新增的 UI（Add）

1. **"更多工具" Hub 页**（`src/ui/pages/tools_page.py`）：展示 Feature Registry 列表，AVAILABLE 项为真实按钮，其余为 Coming Soon 卡片（可点击、弹出对话框、绝不报错）。
2. **Feature Registry 模块**（`src/ui/features.py`）：见 H。
3. **Coming Soon 对话框**（`src/ui/coming_soon.py` 或 `widgets/` 下组件）：统一 `ComingSoonDialog(feature)`，展示状态徽标 + `coming_soon_message`，保证点击任何未上线功能都不崩溃。
4. **#tertiary 按钮 token**（见 B6）。
5. **统一间距 token + 组件级 Design Token 模块**（`src/ui/theme/tokens.py` 或并入 `themes.py`，见 J）。
6. **状态态模板组件**：Loading / Empty / Success / Error / **Coming Soon** 五态统一组件（部分已散布存在：Organize 有 empty/progress/error，History 有 empty；**Coming Soon 态缺失**需补）。
7. **`COPYRIGHT_TEXT` 常量**（`version.py` 或 `features.py`），逐字 `"© 中哥  All Rights Reserved"`。

---

## E. 首页最终布局建议

保持现状收敛方向，最终结构（自上而下）：

```
[Hero 卡片]
  ├─ 左：品牌「桌面文件整理助手」+ 时段问候（P2-7）+ 副文案（只移动不删除可撤销）
  ├─ 右：电脑整洁度 紧凑环（56px）+ 分数 + "电脑整洁度" 标签
  ├─ 文件夹路径输入框 + [选择文件夹](secondary) + [开始扫描](primary)   ← 唯一主操作
  ├─ 支持类型提示行（图片·文档·视频·音频·压缩包·代码·安装程序）
  └─ [♻️ 一键还原最近一次整理](undo-cta，仅存在可撤销记录时可见)
[统计卡片行] 累计整理文件 · 整理次数 · 最近整理   （StatCard，三列）
```

- **ONE PRIMARY ACTION**：首页唯一主操作 = `开始扫描`（primary）。`选择文件夹` 与 `一键还原` 均次级/辅助。
- 整洁度环保留为"轻量氛围指标"，不喧宾夺主（已实现，维持）。

---

## F. 导航最终布局建议

侧栏 `_NAV` 改为六项目（对应需求）：

```
🏠 首页          home
✨ 文件整理       organize
🧰 更多工具       tools      ← 新增（Feature Registry Hub）
🕒 整理历史       history
⚙  设置          settings
ℹ  关于          about      ← 由顶栏移入导航（或保留顶栏+导航双入口，二选一）
```

- 顶栏保留主题切换按钮；"关于"建议**同时**作为导航项（满足需求枚举），顶栏按钮可保留或移除，避免重复。
- `custom`（整理方案）不再作为独立导航；其"按类型/按日期"选择能力已由 Organize 页的 `Segmented` 覆盖，可删除（见 C1，需先改测试）。
- 侧栏底部"🛡 安全整理"卡片（不删除/本地运行/支持撤销）保留，强化安全感。

---

## G. Future Tools 最终布局建议（"更多工具" Hub）

`tools_page.py` 以卡片网格呈现 Feature Registry：

```
[标题] 更多工具
[副标题] 文件整理已上线，更多能力正在路上

┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ 📂 文件整理  │ │ 🔍 重复文件 │ │ 🧹 大文件   │
│ 可用        │ │ 即将推出    │ │ 即将推出    │
│ [立即使用]  │ │ 即将推出→  │ │ 即将推出→  │
└─────────────┘ └─────────────┘ └─────────────┘
   （点击 AVAILABLE 跳 organize；点击 COMING_SOON 弹对话框）
```

- AVAILABLE 项：主按钮 `立即使用` → `navigate.emit("organize")`。
- COMING_SOON / IN_DEVELOPMENT / UNSUPPORTED / DISABLED：整卡可点击，弹 `ComingSoonDialog`，**不报错、不跳转**。
- UNSUPPORTED（如需要 Windows 11 特性但跑在 Win10）：灰显 + 提示最低系统版本。

---

## H. Feature Registry 建议（`src/ui/features.py`）

```python
from dataclasses import dataclass, field
from enum import Enum

class FeatureStatus(str, Enum):
    AVAILABLE = "available"
    COMING_SOON = "coming_soon"
    IN_DEVELOPMENT = "in_development"
    UNSUPPORTED = "unsupported"
    DISABLED = "disabled"

@dataclass
class FeatureDefinition:
    id: str
    name: str
    icon: str
    description: str
    category: str
    status: FeatureStatus
    enabled: bool = True
    min_windows_version: str | None = None
    coming_soon_message: str = ""

FEATURES: list[FeatureDefinition] = [
    FeatureDefinition("file_organize", "文件整理", "📂",
        "按类型或日期整理桌面/下载等文件夹", "整理",
        FeatureStatus.AVAILABLE, enabled=True),
    FeatureDefinition("duplicate_finder", "重复文件查找", "🔍",
        "找出并清理内容相同的重复文件", "整理",
        FeatureStatus.COMING_SOON,
        coming_soon_message="即将推出：基于内容哈希的重复文件检测。"),
    # … 其余 14 项（大文件清理 / 截图归档 / 下载清理 / 命名规范化 等）均 COMING_SOON
]
```

- 初始 16 项：**仅 `file_organize` = AVAILABLE**，其余 COMING_SOON（按需求）。
- 不实现未来功能本身，只登记元数据 + 点击行为。
- 模块**纯 UI/元数据**，不依赖 `core/data` 业务层，风险极低。

---

## I. Coming Soon 交互建议

- 统一 `ComingSoonDialog(feature: FeatureDefinition)`：
  - 标题：`{feature.icon} {feature.name}`
  - 状态徽标：用 `#badge` 或 `#tl-tag` 风格显示"即将推出 / 开发中 / 不支持"。
  - 正文：`feature.coming_soon_message`；若 `UNSUPPORTED` 且 `min_windows_version` 存在，追加"需要 Windows {min_windows_version} 或更高"。
  - 按钮：仅 `知道了`（关闭）。
- **健壮性**：任何 COMING_SOON / UNSUPPORTED / DISABLED 卡片点击都必须落到此对话框，绝不触发业务调用或抛异常（需求硬约束：可点击、显示对话框、不报错）。

---

## J. Design Token 建议

在 `ui/theme/themes.py` 现有基础上补充：

- **间距 scale（4–40）**：`SPACING = {xs:4, sm:8, md:12, lg:16, xl:24, xxl:32, hero:40}`，各页面 `setSpacing/setContentsMargins` 引用而非魔法数字（解决 B7）。
- **圆角**：已有 `radius(14)/radius_sm(10)/radius_xs(8)`，建议补充 `radius_full(999px)`（chip/badge 已用硬编码 999px，可 token 化）。
- **字号层级**（Typography 四级）：`display(24,page-title) / title(18-20) / body(13-14) / caption(11.5-12)`，现有散落字号可归并。
- **颜色语义**：现有 `accent/success/danger/text_muted` 等已语义化，良好；补充 `tertiary_bg`/`tertiary_border`（供 #tertiary 使用）。
- **组件 token 文件**（可选）：`ui/theme/tokens.py` 集中导出 `SPACING`/`RADIUS`/`TYPE`，供组件库引用。

> 现状已有 90% 的地基，J 主要是"补间距/字号/tertiary token + 消除硬编码魔法数"，不是重建。

---

## K. DPI / Windows 兼容性风险

1. **废弃 High-DPI 属性（B5）**：`main.py` 的 `AA_EnableHighDpiScaling`/`AA_UseHighDpiPixmaps` 在 Qt6 废弃；且 PyInstaller one-file 构建**未声明 DPI 感知 manifest**，Windows 可能对程序做位图拉伸（模糊）。→ 建议用 `ctypes.windll.shcore.SetProcessDpiAwareness(2)`（PMv2）或 shcore `SetProcessDpiAwarenessContext(-3)` 在 `QApplication` 前设置，并移除废弃属性。
2. **窗口最小尺寸 900×620 在 200% 缩放下溢出**（实际风险）：
   - 1366×768 @125% → 逻辑宽 ≈1093px（900 可容纳）✅
   - 1366×768 @150% → 逻辑宽 ≈911px（900 临界）⚠️
   - **1366×768 @200% → 逻辑宽 ≈683px < 900 → 窗口比屏幕宽，出现裁剪/滚动条** ❌
   - 建议：要么降低 `setMinimumSize` 到 ~860×600，要么在小于阈值时让内部用 `QScrollArea` 包裹；并在低分高缩放下验证。
3. **自定义绘制控件（ScoreRing/ToggleSwitch）**：用固定像素 + `QPainter`，Qt6 下按 `devicePixelRatio` 自动清晰，风险低；但切换主题时 `ScoreRing` 已 `update()`，`ToggleSwitch` 也 `update()`，OK。
4. **`QGraphicsDropShadowEffect`**：`StatCard` 阴影在主题切换后颜色不过期（B3），属视觉瑕疵非崩溃。
5. **长路径**：业务层 `core/` 已处理 Windows 长路径（不在本 UI 审计范围，确认 UI 层未引入新路径假设即可）。

---

## L. 修改文件清单（按阶段，本阶段零修改）

> 以下为后续 UI-1…UI-10 预计触及文件，**当前 READ ONLY 阶段不改动**。

| 文件 | 阶段 | 改动性质 |
|---|---|---|
| `src/ui/theme/themes.py` | UI-1/UI-7/UI-9 | 补 `#tertiary`、间距/字号 token、`#badge` 用 `{on_accent}`、去冗余 |
| `src/ui/features.py` | UI-3（新增） | Feature Registry 模块 |
| `src/ui/pages/tools_page.py` | UI-4（新增） | 更多工具 Hub |
| `src/ui/coming_soon.py` | UI-5（新增） | Coming Soon 对话框 |
| `src/ui/widgets/sidebar.py` | UI-2 | `_NAV` 增 `tools`/`about` |
| `src/ui/app_shell.py` | UI-2/UI-4 | 路由增 `tools`/`about`，接 `tools_page` |
| `src/ui/pages/dashboard_page.py` | UI-1/UI-9 | `_on_theme` 调 `refresh_shadows`；保持 Hero |
| `src/ui/about.py` | UI-1 | 用逐字 `COPYRIGHT_TEXT` |
| `src/version.py` | UI-1 | 增 `COPYRIGHT_TEXT` 常量 |
| `src/main.py` | UI-9 | DPI 感知改造，去废弃属性 |
| `src/ui/pages/organize_page.py` | UI-7 | `_EXT_BY_LABEL` 收敛（可选） |
| `src/ui/pages/{history,settings,welcome,_page}.py` | UI-6 | 一致性微调（非必须） |
| `tests/test_*.py` | UI-8/UI-10 | 新增 home/tools/registry/coming-soon/about/welcome/dashboard 测试；改 `test_appshell` 以允许移除 `custom` 页 |
| `build.spec` | UI-10 | 清理 shim hiddenimports（仅在 C2 重指向完成后） |

---

## M. 明确哪些文件绝对不能碰（Untouchable）

以下文件属 **业务 / 数据 / 安全 / 数据库契约 / P0 安全** 层，UI 审计与未来功能预留**严禁改动**（需求硬约束）：

- `src/core/scanner.py` — 扫描
- `src/core/classifier.py` — 分类
- `src/core/organizer.py` — 移动/校验/OrganizeResult
- `src/core/rules.py` — 分类规则（`CATEGORY_NAMES`/`DEFAULT_RULES` 等映射**只读引用**，新增扩展分类属数据层决策，须经你确认；本审计仅建议 UI 引用方式，不改其数据）
- `src/data/database.py` — SQLite 表结构
- `src/data/history_repo.py` — 历史表读写
- `src/data/operation_repo.py` — 操作记录 / pending recovery
- `src/data/settings_repo.py` — 设置 KV
- `src/ui/undo.py` — 撤销编排（含 5 步反向顺序、空目录清理）
- `src/ui/state/worker.py` — 后台任务封装
- `src/utils/*` — 路径/长路径/日志/格式化

> **原则**：UI 层只通过现有 `core.*` / `data.*` 公开 API 编排，任何"看起来更顺手"的改法若需动上述文件，一律记为 `[OUT OF SCOPE]` 并停下上报，不自行修改。

---

## 审计结论

- **地基扎实**：token 双主题、按钮层级、首页收敛、四步安全门、分类名 key/display 分离、组件化雏形均已具备，V1.0 无需推翻重建，是"打磨 + 架构预留"。
- **必须修 8 项（B1–B8）**：版权逐字、token 漏填、阴影刷新、导航补全、DPI 改造、tertiary、间距 token、反向映射收敛。
- **架构新增 3 块**：Feature Registry、更多工具 Hub、Coming Soon 对话框 —— 均为纯 UI/元数据，零业务风险。
- **删除需谨慎**：`custom` 页与 3 个 shim 受测试/15+ 模块约束，必须"先改测试/先重指向"再清理。

**下一步**：等待你确认进入 UI-1（Design System 收口）及后续阶段顺序。本阶段未改动任何文件。
