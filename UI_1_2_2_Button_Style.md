# UI-1.2.2 — Button Token / Style Implementation

> 阶段：UI-1.2 子阶段 2/8（UI-1.2.1 = 只读审计，本阶段首次落码）
> 范围：仅 Button 样式 / 变体 / 状态 + 必要的 UI 调用处变体指定。未进入 Card / Typography / Spacing / Theme 架构 / Navigation / Tools Hub / Feature Registry。
> 产品语义裁决（本阶段锁定）：**撤销 / 一键还原 = Accent / Primary-Soft，绝不是 Danger。**

---

## 【阶段】
UI-1.2.2 / Button Token & Style Finalization

## 【修改文件】
| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `src/ui/theme/themes.py` | QSS 样式 | 新增 `#tertiary`；新增全局 `:focus` 焦点环；补齐 `ghost:pressed`、`icon:pressed`；删除死样式 `#link`；删除死样式 `#undo-done`（无实例） |
| `src/ui/pages/organize_page.py` | UI 调用处变体 | 「♻️ 一键还原本次整理」`undo-done` → `undo-cta`；「再整理一次」`ghost` → `tertiary`（给 tertiary 真实用途） |
| `src/ui/pages/history_page.py` | UI 调用处变体 | 「撤销选中整理」`secondary` → `undo-cta`（撤销=Accent-Soft） |
| `src/ui/pages/dashboard_page.py` | 未改 | 首页「一键还原最近一次整理」早已为 `undo-cta`，已符合语义，保持 |
| `src/ui/undo.py` | UI 调用处变体（仅 2 行样式） | 确认弹窗「还原」`danger` → `undo-cta`；「取消」补 `ghost`（详见下方风险说明） |
| `src/ui/preview_report.py` | UI 调用处变体 | 「取消」补 `ghost` 变体（原 generic QPushButton） |

## 【修改内容】
1. **新增 `#tertiary` 变体**：transparent 背景 + transparent 边框 + `text_secondary` 文字；hover 给 `surface_hover` 浅底 + `border_strong` 边框 + `text`；pressed 进一步降至 `surface_alt`。视觉权重 `Primary > Secondary > Tertiary > Ghost`，与规范一致，非 Secondary 缩水版。
2. **全局焦点环**：`QPushButton:focus { outline: 2px solid {accent}; outline-offset: 2px; }` —— 单一规则覆盖 **所有** 变体（primary/secondary/tertiary/ghost/danger/icon），token 驱动、克制、不改变布局。满足 §5「所有按钮具备 :focus」。
3. **补齐 `ghost:pressed` / `icon:pressed`**：按下有明确背景反馈（surface_alt），normal/hover/pressed 三态区分清晰且克制（无缩放/跳动/动画）。
4. **撤销语义统一为 Accent/Primary-Soft**：
   - 首页「一键还原最近一次整理」→ `undo-cta`（原有，符合）
   - Organize「♻️ 一键还原本次整理」→ `undo-cta`
   - History「撤销选中整理」→ `undo-cta`
   - 确认弹窗「还原」→ `undo-cta`；「取消」→ `ghost`
   - 全项目已无任何按钮使用 `danger` 表示撤销；`#undo-done` 死样式（原 danger 红）已删除。
5. **Dialog 按钮层级统一**：取消/返回 = Ghost（弱、左），确认/还原/开始 = Primary 或 Accent-Soft（强、右）。Preview Report 与 ConfirmUndoDialog 均符合。
6. **清理死样式**：`#link`（全项目 0 实例，已搜证）与 `#undo-done`（仅 organize 引用，已改指 undo-cta）删除，避免无效样式堆积。
7. **`tertiary` 真实用途**：Organize 完成页「再整理一次」由 `ghost` 升为 `tertiary`，形成 `返回首页(primary) > 再整理一次(tertiary) > 查看历史/查看失败明细(ghost)` 的清晰层级，满足 §18「#tertiary 已有实际用途」。

## 【未修改内容】
- `core/*`、`data/*`、`ui/state/worker.py`、`utils/*` —— **未触碰**。
- `ui/undo.py` 的**业务逻辑 / 安全机制 / 5 步反向顺序 / Worker 调用** —— **未触碰**；本次仅修改该文件内 2 行按钮 `setObjectName`（纯样式变体指定），未改 import、未改 `run_undo`、未改 `ConfirmUndoDialog` 任何行为。
- Card / Typography / Spacing / Theme 切换架构 / Navigation / Tools Hub / Feature Registry —— 本阶段不涉及（属 UI-1.3 及之后）。
- 版权常量 `COPYRIGHT_TEXT`（`src/version.py`）—— 未改（§21 要求保留）。

## 【Button Matrix】
| Variant | Normal | Hover | Pressed | Focus | Disabled |
|---|---|---|---|---|---|
| **Primary** | accent 底 / on_accent 字 / 600 | accent_hover 底 | accent_pressed 底 | 全局 accent 2px outline | text_muted 字 / surface_alt 底 / border |
| **Secondary** | surface_alt 底 / text 字 / border_strong / 600 | surface_hover 底 / accent 边框 | border 底 | 全局 accent 2px outline | 同 Disabled 基样式 |
| **Tertiary** | transparent 底 / text_secondary 字 / transparent 边框 / 600 | surface_hover 底 / border_strong / text | surface_alt 底 / text | 全局 accent 2px outline | 同 Disabled 基样式 |
| **Ghost** | transparent 底 / text_secondary 字 | surface_hover 底 / text | surface_alt 底 / text | 全局 accent 2px outline | 同 Disabled 基样式 |
| **Danger** | surface 底 / danger 字 / danger 边框 | danger_soft 底 | danger_soft 底 | 全局 accent 2px outline | 同 Disabled 基样式 |
| **Icon** | surface 底 / border / radius_xs / 15px | surface_hover 底 / accent 边框 | surface_alt 底 | 全局 accent 2px outline | 同 Disabled 基样式 |
| **Disabled**（基） | text_muted 字 / surface_alt 底 / border | — | — | 全局 accent 2px outline | — |

> 注：Focus 列为全局统一规则，覆盖所有变体；Disabled 视觉由基础 `QPushButton:disabled` 提供，文字保持可读（`text_muted` 非纯灰消失）、边框明确，不出现「软件坏了」观感。

## 【Undo Semantic】
**Undo = Accent / Primary-Soft（≠ Danger）。**
- 全部撤销入口（首页 / Organize 完成页 / History / 确认弹窗）统一使用 `undo-cta`（accent_soft 浅底 + accent 字 + accent 边框），hover 反白。
- Danger 仅保留给未来真正破坏性操作（永久删除 / 清空不可恢复数据 / 删除重要配置）。
- 对比度校验：Light `bg=#EEF2FF text=#4F46E5`；Dark `bg=#272058 text=#818CF8`，双主题均清晰可读。

## 【测试结果】
- `python -m compileall -q src main.py` → **PASS**
- `test_core / test_security / test_reliability / test_windows_paths / test_p2_coverage` → **全部 PASS**

## 【UI 验证】
- Headless 渲染校验（Light + Dark）：均无未替换 token；`#tertiary` 三态齐全；`ghost:pressed`、`icon:pressed` 存在；全局 `:focus` outline 存在；`#link`、`#undo-done` 已从生成样式中移除。
- 静态语义校验：上述 9 项 undo/变体映射断言全部 PASS（含「无任何 undo 使用 danger」「无 undo-done 残留」）。
- QSS 解析：Qt 对非法规则仅静默忽略，不会致构造崩溃；本次新增规则均为标准 QSS 属性。

## 【风险】
- **⚠️ `ui/undo.py` 触碰说明**：本阶段「禁止修改」清单含 `ui/undo.py`，但同一指令的 §7 明确要求确认弹窗「还原→Accent-Soft / 取消→Ghost」，且该弹窗按钮仅存在于 `ui/undo.py`。本次**仅改 2 行 `setObjectName`（纯样式）**，未动任何撤销逻辑/安全/Worker。若你认为 `ui/undo.py` 应完全冻结，唯一回退即恢复这 2 行（但「还原」将退回 `danger`，与已锁定的「撤销≠Danger」产品语义冲突）。请裁定是否接受。
- **焦点环 `outline` 兼容性**：`outline` 为 Qt QSS 标准属性，但极老版本可能忽略该规则。若实测焦点环不显示，回退方案为焦点态改用 `border` 高亮（需保证 1px 不变以维持布局）。当前按标准实现。
- 其余风险：极低（纯 QSS 重指向 + 调用处变体指定，无布局/逻辑变化）。

## 【下一阶段】
**UI-1.2.3 — Primary / Secondary 落地确认**。本阶段已新增 tertiary/ghost-pressed/icon-pressed 并统一 undo 语义；UI-1.2.3 将复核 Primary/Secondary 在首页与整理流程中的视觉层级是否符合 §15/§16（主操作唯一、下一步清晰），无新样式需求时仅做静态确认报告。

---

### 执行纪律
- 完成 UI-1.2 全部子阶段后**不会**自行进入 UI-1.3（Card System）/ UI-2（Tools Hub / Feature Registry / Coming Soon）。
- 每子阶段单独报告、单独停止、等待确认。
