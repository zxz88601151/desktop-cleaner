# Desktop Cleaner UI-1.3 — Figma Blueprint（高保真设计规范）

> 任务 §30–§31。非线框，而是可直接指导 PySide6 实现的规格。统一基线：
> **窗口** 1080×760（min 900×620）｜**字体** Segoe UI / Microsoft YaHei 13px｜**圆角** Card 8 / Control 6 / Small 4｜**Accent** `#2B6CB0`｜**无阴影**（靠 border）｜**图标** 线型 16/20/22。

---

## 01 · 整理首页 Dashboard
- 布局：左 220px 导航栏 + 右内容区（28/24 边距）。
- Hero：标题"整理文件" + 副文"选择文件夹，扫描并分类整理 — 文件只移动、不删除、可撤销"；文件夹 `QLineEdit`（占位"例如：桌面 / 下载"）+ [选择文件夹](secondary) + [扫描](primary)。
- **无整洁度圆环**；下方"最近整理"真实摘要（线型图标 + 数据）；存在可撤销记录时显示 [撤销最近一次整理](undo-cta，无 emoji)。
- Empty：首次无历史时显示"还没有整理记录，选择一个文件夹开始整理"。

## 02 · Folder Picker
- 复用系统 `QFileDialog.getExistingDirectory`（原生，非自绘）。触发源：Hero [选择文件夹]、整理页同款。

## 03 · Scanning（扫描中）
- 复用 Organize 页 progress 区：状态行"正在扫描：{root} …" + 不确定进度条（indeterminate）。可选显示"已检查 N / M 个文件"（若有计数）。无"正在智能分析"类模糊文案。

## 04 · Scan Result（扫描结果）
- 同 Organize 预览列表：`#summary-line`"共 N 个文件 · X MB，建议分为 K 类"；每类一行（线型分类图标 + 名称 + 计数/大小 + 扩展名 + 占比条）；下方 [开始整理](primary)。

## 05 · Preview / Confirmation（预览确认 — 范本）
- `PreviewReportDialog`：标题"整理模拟报告"；目标文件夹；整理方式；"本次将整理 N 个文件（共 X MB），文件仅移动、不删除，可随时撤销"；分类表（线型图标+分类 / 目标文件夹 / 文件数 / 大小）；移动明细预览列表；提示"文件不会删除，可随时撤销"；[取消](ghost) [开始整理](primary)。

## 06 · Cleaning Progress（执行中）
- 同 Scanning 但状态"开始整理…"；真实进度（已移动/总数）；完成后切到 07。

## 07 · Cleaning Complete（完成 — 不过度庆祝）
- 标题"整理完成"（20px/700，非 32px 大标题）；中性对勾线型图标（非 ✅ emoji）；"已移动 N 个文件到分类文件夹"；分类明细（线型图标 名称 计数）；[撤销本次整理](undo-cta) [返回首页](primary) [查看历史](ghost) [再整理一次](tertiary)；失败时出现 [查看失败明细](ghost)。

## 08 · Undo（撤销确认 — 范本）
- `ConfirmUndoDialog`：线型撤销图标（非 ♻️）；"撤销本次整理？"；"将把 N 个文件还原回原文件夹：{root}"；整理时间；"文件只移动、不删除。还原后可在整理历史中再次整理"；诚实提示冲突；[取消](ghost) [还原](undo-cta)。

## 09 · History（历史）
- 标题"整理历史" + 副文"每一次整理都记录在案，可随时一键撤销还原"。时间线行：线型图标（类型/日期）+ "#id · 相对时间" + "按类型整理 · 整理 N 个文件" + 源路径 + 状态标签（已完成/已撤销/失败，语义色小标签非胶囊）；选中行高亮；底部 [撤销选中整理](undo-cta) [返回首页](ghost)。

## 10 · History Detail
- 点击行展开/弹窗：该次整理的源、模式、分类计数、操作列表（可滚动），[撤销](undo-cta)。（当前以行选中 + 底部撤销实现，可保留或加详情弹窗。）

## 11 · Settings（设置 — 样板）
- 分组行（set-row，border-bottom 分隔）：深色模式(toggle) / 默认整理方式(segmented) / 包含子文件夹(toggle) / 检查更新(ghost 按钮) / 关于(primary 按钮)。每行至左标签+说明，右控件。标题"设置" + "偏好会立即生效并自动保存"。

## 12 · About（关于）
- 名称 + "版本 1.1.0 · 桌面文件整理助手" + TAGLINE + 分隔 + 功能列表（**纯文本或线型图标，去 emoji**）+ 版权"© 中哥 All Rights Reserved" + [关闭](primary)。

## 13 · Update Available（更新可用）
- `UpdateDialog`：版本 NORMAL/IMPORTANT/FORCE 三档；展示新版本号、更新说明、[稍后](ghost) [前往下载](primary，打开下载页)。无强制动画。

## 14 · Forced Update（强制更新）
- 同 13 但 FORCE 档：弱化"稍后"，强调必须更新（仍走下载页，不自助替换 EXE，符合 RULE-0/安全）。

## 15 · Error / Permission Denied（错误）
- 标题"无法访问此文件夹"；What：具体原因（如"当前账户没有访问权限"）；Why：简短；What to do："请检查文件夹权限后重试"；[重新选择](secondary)。禁止"哎呀😅"。

## 16 · Empty State（空状态）
- 各列表空时：居中标题(14/600) + 副文(12/muted) + 明确下一步按钮（如历史空→[选择文件夹开始整理]；整理未扫描→"选择文件夹后点击开始扫描，我们会先预览再整理"）。无大插画/营销图。

## 17 · Loading State
- 启动/重载：窗口即时显示，后台 `QTimer.singleShot` 延迟更新检查（已有）；长任务用 progress 条 + 状态行，不阻塞；无全屏 spinner overlay 装饰。

---

## 全局交互规范
- **Hover**：surface_hover 浅底 + accent 边框（按钮/导航/卡片统一）。
- **Focus**：2px accent 描边、无布局位移（已有，保留）。
- **Disabled**：text_muted + surface_alt 底。
- **Dialog**：modal，Enter=主操作，Esc/X=取消。
- **键盘**：Tab 可达所有控件；图标按钮补 Tooltip。

---
*READ-ONLY 审计产物。以上为实施蓝图，待 MIGRATION_PLAN 批准后落地。*
