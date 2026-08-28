# Desktop Cleaner UI-1.3 — Design System（新版视觉规范）

> 本文件定义重构后的 Design Token 与组件样式规范，直接指导 PySide6 实现。
> 原则来源：任务 §7–§34。当前实现对照见 `src/ui/theme/themes.py`。

---

## 1. 设计原则（§34，写入产品核心）

| # | 原则 | 落地含义 |
|---|------|---------|
| 01 | **Task First** | 每个页面第一焦点是"当前要做什么"，而非装饰 |
| 02 | **Information Before Decoration** | 信息密度优先，装饰服务于可读性 |
| 03 | **Familiar Before Novel** | 用 Windows 用户已熟悉的控件与布局 |
| 04 | **Quiet UI** | 界面安静，不抢注意力 |
| 05 | **Predictable Interaction** | 每次点击结果可预期 |
| 06 | **Trust Before Delight** | 文件操作工具先建立信任（预览/可撤销/本地） |
| 07 | **Fast Path First** | 高频路径最短（选文件夹→扫描） |

---

## 2. 语义颜色（§11：中性为主，Accent 为辅）

**变更点**：① 去除蓝紫 `#4F46E5`，改为更克制、偏"工具蓝"的强调色；② 明确语义色；③ 禁止渐变/发光/多 Accent 竞争。

```text
Accent            — 单一强调色，仅用于主操作/激活态/聚焦环
Background        — 应用底色（浅色冷灰，非纯白刺眼）
Surface           — 卡片/面板底
Surface Alt       — 交替行/二级底
Border            — 默认描边
Border Strong     — 输入框/分割强调
Text Primary      — 主文字
Text Secondary    — 次要文字
Text Muted        — 辅助/禁用
Success / Warning / Error — 状态（克制使用，非装饰）
```

### 2.1 推荐 Token 值（提案 vs 现状）

| Token | 现状 (LIGHT) | 提案 (LIGHT) | 理由 |
|---|---|---|---|
| `accent` | `#4F46E5`（蓝紫 indigo） | `#2B6CB0`（工具蓝，沉稳） | 去除蓝紫；接近 Windows 蓝但更内敛 |
| `accent_hover` | `#4338CA` | `#235789` | 同系加深 |
| `accent_pressed` | `#3730A3` | `#1C4A73` | 同系 |
| `accent_soft` | `#EEF2FF` | `#EAF1F8` | 浅底跟随 |
| `bg` | `#F4F6FB` | `#F3F4F6` | 更中性灰 |
| `radius` | `14px` | `8px` | §9 控制夸张圆角 |
| `radius_sm` | `10px` | `6px` | |
| `radius_xs` | `8px` | `4px` | 控件圆角 |
| `shadow` | `rgba(15,23,42,0.10)` | **删除**（改靠边框） | §10 少用阴影 |

> 深色主题同步：accent `#818CF8`→`#6CA0DC`；`bg` 保持 `#0B1120` 或略提亮至 `#0E1525` 降压迫感；radius 同比例下探至 `8/6/4`。

---

## 3. Typography（§7.1：四级以上，克制无装饰）

| 角色 | 字号 | 字重 | 用途 | 现状对照 |
|---|---|---|---|---|
| Page Title | 20px | 700 | 页标题 | 现状 24px → **降至 20** |
| Section Title | 14px | 600 | 分区标题 | 现状 14px ✅ |
| Body | 13px | 400 | 正文 | 13px ✅（Windows 习惯） |
| Secondary | 12.5px | 400 | 说明/副文 | ✅ |
| Caption | 11.5px | 400 | 注释/版权 | ✅ |
| Label | 13px | 600 | 表单标签 | ✅ |
| Button | 13px | 600 | 按钮文字 | ✅ |

**禁止**：巨型标题、装饰字体、渐变文字、发光文字。
**字体族**：保留 `"Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif`（Windows 原生优先）。

---

## 4. Spacing（§8：统一尺度，禁随机值）

```text
基准尺度：4 / 8 / 12 / 16 / 24 / 32 / 48
```
- 页面外边距：`28 24`（保持）
- 区块间距：主要用 `16 / 24`
- **禁止**出现 `13 / 19 / 27 / 31 / 37` 等无理由奇数（现状 `radius` 无关；但按钮 padding `8px 18px` 等保留，因属 8 倍数体系内）。

---

## 5. Radius（§9：统一收敛）

```text
Card / Panel  : 8px   (现状 14 → 8)
Dialog        : 8px
Control/Input : 6px   (现状 8 → 6)
Small/Chip    : 4px
```
- 取消 `999px` 胶囊徽章（现状 `#badge`/`#chip`/`#tl-tag` 用 `999px`）→ 改 `4px` 或 `6px` 圆角小标签，降低"彩色状态块"噪声。

---

## 6. Shadow（§10：默认不用）

- **政策**：卡片/面板/对话框一律**不用投影**，依靠 `border` + `surface` 层级区分。
- 移除 `dashboard.py` 的 `QGraphicsDropShadowEffect`（`StatCard._apply_shadow`）。
- 仅对话框在必要时可用极淡 1px 边框内阴影（可选，非必须）。

---

## 7. Icon System（§12：统一线型，禁 emoji）

**核心修复项**。建立 `ui/icons.py` 单一图标模块，使用 `QPainter` 绘制**单色线性图标**（复用现有 `sidebar._logo_pixmap()` 的绘制范式，零新增依赖），按语义命名：

```text
icon_home        🏠→ 线性房子
icon_organize    ✨→ 线性整理/扫帚（中性）
icon_history     🕒→ 线性时钟
icon_settings    ⚙ → 线性齿轮
icon_folder      📁→ 线性文件夹
icon_undo        ♻️→ 线性回转箭头
icon_check       ✓ → 线性对勾（保留文本符号亦可）
icon_type        🗂️→ 线性分类
icon_date        📅→ 线性日历
icon_safe        🛡→ 线性盾牌
icon_category_*  📂🔒🔍…→ 各分类线性图标（或纯文字标签）
icon_theme       🌙/☀️ → 线性月/日（或纯文字"浅色/深色"）
```
- 所有图标继承 `text`/`accent` 单色，随主题切换；统一 `size=16/20/22`，`stroke-width` 一致。
- **删除** `core.category_emoji` 在 UI 层的 emoji 用法，改为 UI 侧图标映射（core 逻辑不动）。

---

## 8. Button System（§13：四级清晰）

| 类型 | 用途 | 样式要点 |
|---|---|---|
| **Primary** | 扫描 / 整理 / 确认 | accent 实心，白字，字重 600 |
| **Secondary** | 选择文件夹 / 取消 | surface_alt 底 + border_strong |
| **Tertiary** | 查看详情 / 更多 | 透明底，text_secondary，hover 浅底 |
| **Ghost** | 关闭 / 返回 / 取消 | 透明无边框，仅文字 |
| **Danger** | 删除类危险操作 | 当前产品无删除操作，预留红色样式，不可用其表达撤销 |

> 现状按钮层级已冻结（UI-1.2.8），**本阶段只替换其中的 emoji 图标与个别文案**，不重构按钮机制。

---

## 9. 组件样式规范速查

| 组件 | 规范 |
|---|---|
| Input / ComboBox | 1px border_strong，6px 圆角，focus → accent 边框 |
| Card / Panel | surface 底 + 1px border，**无阴影**，8px 圆角 |
| Dialog | bg 底，8px 圆角，标题 20px/700，按钮右对齐（取消/主操作） |
| List / Table | 1px border，alternate surface_alt，行高 8px 内边距 |
| Progress | 8px 高，accent 填充，无圆角光晕；不确定态用 indeterminate |
| Badge / Tag | 4–6px 圆角小标签，语义色克制，禁用 999px 胶囊 + 大面积彩色 |
| Navigation | 左侧 200–220px 栏，文字 + 线型图标，激活态 accent_soft 底 |
| Tooltip | 系统原生，补 `setToolTip` 于图标/无文字按钮 |
| Empty State | 居中标题(14/600) + 副文(12/muted) + 明确下一步按钮 |
| Error State | What/Why/What-to-do 三段，具体文案，提供"重试/重新选择" |

---

## 10. Windows 原生感对齐清单（§25）

- [x] 高 DPI 缩放已开（`main.py:33-34`）— 保留
- [ ] 图标改系统一致线型（§7）
- [ ] 对话框使用 `QDialogButtonBox` 原生按钮顺序（取消在左/主操作在右，符合中文 Windows）— 现状部分已用，统一
- [ ] 滚动条/下拉用原生 Fusion/Windows metrics
- [ ] 去除所有 emoji（避免跨平台豆腐块）
- [ ] 窗口最小尺寸 `900×620` 保留（响应式下限）
- [ ] 键盘：Tab 顺序、Enter 默认、Esc 关闭、focus 环（现状 `QPushButton:focus` 2px accent 无位移 ✅ 保留）

---
*READ-ONLY 审计产物，未修改源码。Token 值为提案，待人工批准后由 MIGRATION_PLAN 落地。*
