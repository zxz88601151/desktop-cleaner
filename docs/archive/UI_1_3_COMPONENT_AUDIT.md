# Desktop Cleaner UI-1.3 — Component Audit（组件级审计）

> 任务 §29。对每个组件给出 **KEEP / MODIFY / REPLACE / REMOVE** 判定与理由。

---

## 组件清单与判定

### 1. Button — `themes.py` `#primary/#secondary/#tertiary/#ghost/#danger/#icon`
- **判定**：**KEEP 机制，MODIFY 细节**
- **理由**：五级层级已冻结（UI-1.2.8），语义清晰（撤销一律 `undo-cta`，无 danger 误用）。仅修：① 去除按钮内 emoji（♻️ 等）；② `#icon` 主题按钮 emoji（🌙/☀️）→ 线型或纯文字；③ 圆角由 8px→6px（随 token）。
- **风险**：无。不改按钮架构。

### 2. Card / Panel — `#card/#panel/#step-card/#plan-card/#tool-card`
- **判定**：**MODIFY**
- **理由**：去投影（`dashboard.py` 的 `QGraphicsDropShadowEffect` 移除，靠 border 区分）；圆角 14→8；`#plan-card`/`#tool-card` 保留结构但去 emoji 图标（`#plan-emoji`/`#tool-icon`）。

### 3. Input / ComboBox — `QLineEdit, QComboBox`
- **判定**：**KEEP**
- **理由**：1px border + focus accent，符合 Windows。仅圆角 8→6（随 token）。

### 4. Dialog — `QDialog` + `QDialogButtonBox`
- **判定**：**KEEP 结构，MODIFY 文案/图标**
- **理由**：`PreviewReportDialog`/`ConfirmUndoDialog`/`WelcomeDialog`/`AboutDialog` 结构成熟、按钮顺序正确。修：去除 emoji 图标（✅/♻️/🌙）；Coming Soon 弹窗 → **REMOVE**。

### 5. Progress — `QProgressBar`
- **判定**：**KEEP**
- **理由**：8px 高、accent 填充、支持 indeterminate（`organize_page._start_scan` 用 `setRange(0,0)`）。符合 §15 真实进度。无需改。

### 6. Badge / Tag — `#badge/#chip/#tl-tag/#tool-badge`
- **判定**：**MODIFY**
- **理由**：取消 `999px` 胶囊，改 4–6px 小标签；降低大面积彩色（语义色克制）。

### 7. Navigation — `sidebar.py` `#nav-item`
- **判定**：**MODIFY**
- **理由**：导航项去 emoji（🏠✨🕒🧰⚙→线型）；重命名"智能整理"→"整理"；移除"更多工具"项；宽度 240→建议 220；激活态保持 `accent_soft`。

### 8. Table / List — `QTableWidget/#tl-row/#history`
- **判定**：**KEEP 结构，MODIFY 图标**
- **理由**：历史时间线、预览表格结构好。去 emoji 行图标（✨/📅/📁→线型或纯文字）。

### 9. Toast / Message — `QMessageBox`
- **判定**：**KEEP**
- **理由**：错误/完成提示用具体文案（"已还原 N 个文件"），无"哎呀😅"类。保持。

### 10. Tooltip — `setToolTip`
- **判定**：**MODIFY（补强）**
- **理由**：无文字图标（主题按钮、导航图标）补 `setToolTip`，提升可访问性（§24）。

### 11. Empty State — `#empty-title/#empty-sub`
- **判定**：**MODIFY 文案**
- **理由**：历史空状态"去「智能整理」整理一次吧"改"还没有整理记录，选择一个文件夹开始整理"。风格已简洁，保留结构。

### 12. Error State — `QMessageBox.critical`
- **判定**：**KEEP**
- **理由**：已有 What/Why/What-to-do（如 `_on_error` 具体 msg）。保持；未来可抽统一错误模板（非必须）。

### 13. Icon — emoji 全局
- **判定**：**REPLACE**
- **理由**：建立 `ui/icons.py` 线型图标模块（§12，零依赖，QPainter 绘制），替换全部 emoji（导航/统计/分类/完成/撤销/关于/主题/功能列表/Coming Soon）。**最高杠杆去味项**。

### 14. Score Ring — `score_ring.py` + `#score-v 56px`
- **判定**：**REMOVE（首页 Hero 中）**
- **理由**：装饰性"电脑整洁度"指标，无强任务映射（无历史时恒 86）。从首页 Hero 移除；`ScoreRing` 控件可保留用于"整理中"真实进度环（organize 执行态），但不再作整洁度展示。

### 15. Stat Card — `dashboard.py StatCard`
- **判定**：**MODIFY**
- **理由**：去 emoji（📁🔄🕒→线型）、去投影、降圆角。内容（累计文件/次数/最近）保留，属真实摘要。

---

## 汇总

| 判定 | 组件 |
|---|---|
| KEEP | Input, Progress, Toast/Message, Error State, Button(机制) |
| MODIFY | Button(细节), Card, Badge/Tag, Navigation, Table/List, Empty State(文案), Stat Card, Tooltip(补强) |
| REPLACE | Icon(emoji→线型) |
| REMOVE | Score Ring(首页), Tools Page, Coming Soon Dialog |

> 无任何组件需要"重写架构"——印证 **B. REFACTOR** 结论。

---
*READ-ONLY 审计产物，未修改源码。*
