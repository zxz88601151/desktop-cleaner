# UI-1.2.4 — Tertiary / Ghost Final Review（READ ONLY · 零代码改动）

> 阶段性质：只读审计。本报告**未修改任何文件**，未改 QSS / token / 布局 / 样式 / 业务 / 结构。
> 审计基准：UI-1.2.2 完成后的当前源码 + `src/ui/theme/themes.py` 实际 QSS 定义（已逐行比对 normal/hover/pressed 三态）。

## 【阶段】
UI-1.2.4 / Tertiary·Ghost 复核（UI-1.2 子阶段 4/8）

## 【审计范围】
Tertiary / Ghost / Dialog / 完成页 / Dormant Page（结合 `themes.py` 真实渲染权重判断，不止看 objectName）

---

## 实际渲染权重比对（来自 `themes.py` 行 181–221）

| 维度 | Secondary (L181) | Tertiary (L194) | Ghost (L209) |
|---|---|---|---|
| normal 背景 | `surface_alt`（浅灰填充 #F1F5F9） | `transparent` | `transparent` |
| normal 边框 | `1px solid border_strong`（可见 #CBD5E1） | `1px solid transparent` | `1px solid transparent` |
| normal 文字色 | `text`（最深 #0F172A） | `text_secondary`（#475569） | `text_secondary`（#475569） |
| normal 字重 | 600 | 600 | 400（默认） |
| hover 背景 | `surface_hover` | `surface_hover` | `surface_hover` |
| hover 边框 | `border accent` | `border_strong` | （无） |
| hover 文字 | `text` | `text` | `text` |
| pressed 背景 | `border` | `surface_alt` | `surface_alt` |

**判读**：Secondary 在 normal 态即有「填充背景 + 可见边框 + 最深文字」，视觉权重显著高于 Tertiary/Ghost，差异明确 ✅。Tertiary 与 Ghost 的 normal 态**背景、边框、文字色三者完全相同，唯一差异是字重 600 vs 400**——这是本阶段唯一需要记录的层级薄弱点（见 P2-A）。

---

## 【Tertiary Inventory】
| 页面 | 按钮 | 当前 Variant | 是否合理 |
|---|---|---|---|
| 整理-完成 | 再整理一次 | `tertiary` | ✅ 合理 — 弱辅助再操作，位于 Primary 之下、Ghost 之上，语义恰当 |

**结论**：全项目仅 1 处 Tertiary，且用途正确（「再整理一次」非主操作、非关闭/返回类）。
**无**「本应 Secondary 却用 Tertiary」「本应 Ghost 却用 Tertiary」的错配 ✅。

---

## 【Ghost Inventory】
| 页面 | 按钮 | 当前 Variant | 是否合理 |
|---|---|---|---|
| 顶栏 | 关于 | `ghost` | ✅ 合理 — 极弱入口 |
| 历史页 | 返回首页 | `ghost` | ✅ 合理 — 导航返回 |
| 整理方案（离导航） | 返回首页 | `ghost` | ✅ 合理 — 导航返回（休眠页，见 Dormant） |
| 整理-完成 | 查看历史 | `ghost` | ✅ 合理 — 低权重查看 |
| 整理-完成 | 查看失败明细 | `ghost` | ✅ 合理 — 默认隐藏，失败时出现 |
| 撤销确认弹窗 | 取消 | `ghost` | ✅ 合理 — 弱操作，配对「还原(undo-cta)」 |
| 预览报告弹窗 | 取消 | `ghost` | ✅ 合理 — 弱操作，配对「开始整理(primary)」 |

**结论**：Ghost **全部用于 取消/关闭/返回/低权重查看**，无重要操作被误降为 Ghost ✅。
**无**「真正重要操作错放 Ghost」的滥用 ✅。

---

## 【Semantic Hierarchy】
**Secondary > Tertiary > Ghost 是否成立？—— 成立，但 Tertiary↔Ghost 间隙偏薄。**

- Secondary 明显强于 Tertiary：填充背景 + 可见边框 + 最深文字（600）vs 透明 + 无边框 + 灰字（600）。差距显著 ✅
- Secondary 明显强于 Ghost：同上 + Ghost 字重仅 400。差距显著 ✅
- Tertiary 高于 Ghost：仅 `font-weight 600 vs 400`；背景/边框/文字色完全一致。差距**存在但偏薄**（见 P2-A）。

整体链路 `Primary > Secondary > Tertiary(600) > Ghost(400)` 形式成立；产品语义上三者承担不同角色（次级行动 / 弱辅助行动 / 可忽略权重），无语义错位。

---

## 【完成页】（§九 明确判断）
| 操作 | Variant | 判定 |
|---|---|---|
| 返回首页 | `primary` | ✅ 按 §8 设计意图，第一焦点 |
| 一键还原 | `undo-cta`（Accent Soft） | ✅ 安全退路，accent-soft 次之且不可太弱 |
| 再整理一次 | `tertiary` | ✅ 合理 |
| 查看历史 | `ghost` | ✅ 合理 |
| 查看失败明细 | `ghost` | ✅ 合理（默认隐藏） |

**五项结论全部成立 → 不修改** ✅。

---

## 【Dialog】（§十 / §十一）
| 弹窗 | 取消/关闭 | 确认/强操作 | 判定 |
|---|---|---|---|
| 撤销确认 | 取消 = `ghost` | 还原 = `undo-cta` | ✅ 弱/强正确 |
| 预览报告 | 取消 = `ghost` | 开始整理 = `primary` | ✅ 弱/强正确 |
| 关于 | — | 关闭 = `primary`（单按钮） | ✅ §十一 PASS / P2 accepted |

**无**「取消/返回」被误设为 Primary / Secondary 的情况 ✅。
**关于单按钮 Dialog**：唯一操作即关闭，符合 §十一「单按钮 Dialog 可 PASS / P2 accepted」，不强制修改 ✅。

---

## 【发现问题】

### NO P0
### NO P1

### P2（仅 1 项本阶段新发现，其余为已记录/可接受项）
- **P2-A（新）**：Tertiary 与 Ghost 在 normal 态视觉差异过薄——仅 `font-weight 600 vs 400`，背景/边框/文字色完全相同。按 §八触发条件（差异过小）记录。
  - 影响：极低（两者本就同属低强调档；hover 态 Tertiary 多一条 `border_strong` 边框，已区分）。
  - 建议（归属后续阶段，本阶段不改）：给 Tertiary normal 态增加一个更明确但克制的区分，例如常驻 `1px solid border_subtle`（新 token 或复用 `border`）+ 文字色略强于 Ghost，使「弱辅助」与「可忽略」拉开半档。或仅将 Ghost 文字色降为 `text_muted`，拉大两者色差。
  - 处置：**仅记录，不修改**。

---

## 【Accepted Notes】（§十六，已记录/可接受，不扩大范围）
- **About 单按钮「关闭」= Primary**：§十一 PASS / P2 accepted，单按钮弹窗影响极小，不强制修改。
- **完成页按钮较密（5 个，实际可见 4）**：层级清晰（1 primary / 1 undo-cta / 1 tertiary / 2 ghost），记为 UI Complexity Note，非缺陷。
- **preview_report Enter Default**：`ok_btn`/`cancel_btn` 未显式 `setDefault(True)`；QDialog 默认 Esc=`reject`（取消）✅，但 Enter 可能落到首个控件（取消 ghost），与「强操作优先」略悖。归属 **UI-1.2.6 或 UI-1.8**（同 UI-1.2.3 P2-4）。本阶段只读，不修改。
- **custom_page 离导航 2 Primary**：休眠页（Phase 2 已移出导航仅保留注册），记为 Dormant UI Note，非活跃流程缺陷（同 UI-1.2.3 P2-1）。

---

## 【代码修改】
**NONE** —— 本报告为零代码改动只读审计。未触碰 `core/*`、`data/*`、`ui/undo.py`、`ui/state/worker.py`、`utils/*`，亦未改任何 UI 样式/布局文件。

## 【测试】
本阶段 READ ONLY，按 §十五静态检查即可。全量 Variant 枚举：
- `#primary` ×10、`#secondary` ×2、`#tertiary` ×1、`#ghost` ×7、`#undo-cta` ×4、`#danger` ×0、`#icon` ×1
- 与 UI-1.2.2 / UI-1.2.3 一致，无语义错位、无回归迹象。
> 基线（UI-1.2.2）：`compileall` PASS；5 套测试全 PASS。

## 【下一阶段】
**UI-1.2.5 — Danger / Undo Semantic Review**（执行顺序下一子阶段）。但**不得自行进入**，等待确认。
