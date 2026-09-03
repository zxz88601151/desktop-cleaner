# UI-1.2.3 — Primary / Secondary Hierarchy Review（READ ONLY · 零代码改动）

> 阶段性质：只读审计。本报告**未修改任何文件**，未改任何样式/布局/业务逻辑。
> 审计基准：UI-1.2.2 完成后的当前源码（`src/ui/**` 全量 `setObjectName` + `QPushButton` 静态枚举）。

## 【阶段】
UI-1.2.3 / Primary·Secondary 层级复核（UI-1.2 子阶段 3/8）

## 【审计范围】
| 页面 / 弹窗 | 文件 |
|---|---|
| 首页 Dashboard | `src/ui/pages/dashboard_page.py` |
| 整理页（配置/预览/完成三态） | `src/ui/pages/organize_page.py` |
| 历史页 | `src/ui/pages/history_page.py` |
| 整理方案页（已离导航，仅保留注册） | `src/ui/pages/custom_page.py` |
| 设置页 | `src/ui/pages/settings_page.py` |
| 欢迎弹窗 | `src/ui/welcome.py` |
| 关于弹窗 | `src/ui/about.py` |
| 撤销确认弹窗 | `src/ui/undo.py` |
| 预览报告弹窗 | `src/ui/preview_report.py` |
| 顶栏 | `src/ui/app_shell.py` |

---

## 【Primary Inventory】
| # | 页面 | 按钮 | 是否 Primary | 是否合理 | 备注 |
|---|---|---|---|---|---|
| 1 | 首页 | 开始扫描 | ✅ Primary | ✅ 合理 | 页面唯一主 CTA |
| 2 | 整理-配置 | 开始扫描 | ✅ Primary | ✅ 合理 | 与「选择文件夹(secondary)」配对，唯一主操作 |
| 3 | 整理-预览 | 开始整理 | ✅ Primary | ✅ 合理 | 确认执行，唯一主操作 |
| 4 | 整理-完成 | 返回首页 | ✅ Primary | ⚠️ 见 P2-5 | 导航动作标 Primary；按 §8 设计意图可接受 |
| 5 | 整理方案(离导航) | 选择文件夹 | ✅ Primary | ⚠️ 见 P2-1 | 与「开始整理」并列 Primary |
| 6 | 整理方案(离导航) | 开始整理 | ✅ Primary | ⚠️ 见 P2-1 | 与「选择文件夹」并列 Primary |
| 7 | 欢迎弹窗 | 开始使用 | ✅ Primary | ✅ 合理 | 弹窗唯一按钮 |
| 8 | 关于弹窗 | 关闭 | ✅ Primary | ⚠️ 见 P2-2 | 单按钮弹窗，标 Primary 略非常规 |
| 9 | 设置页 | 关于本软件 | ✅ Primary | ✅ 合理 | 页面唯一按钮 |
| 10 | 预览报告弹窗 | 开始整理 | ✅ Primary | ✅ 合理 | 强操作，与「取消(ghost)」配对 |

**结论**：所有**活跃导航可达页面**最多只有 **1 个 Primary**；无「两个同等级 Primary 并列争夺焦点」问题。

---

## 【Secondary Inventory】
| # | 页面 | 按钮 | 是否 Secondary | 是否合理 | 备注 |
|---|---|---|---|---|---|
| 1 | 首页 | 选择文件夹 | ✅ Secondary | ✅ 合理 | 次级动作，配对主 CTA「开始扫描」 |
| 2 | 整理-配置 | 选择文件夹 | ✅ Secondary | ✅ 合理 | 次级动作，配对主 CTA「开始扫描」 |

**结论**：Secondary **仅用于「选择文件夹」**这一明确的次级动作，无「本应 Tertiary/Ghost 却用 Secondary」的滥用。保留克制 ✅。

---

## 【Tertiary Inventory】
| # | 页面 | 按钮 | 是否 Tertiary | 是否合理 | 备注 |
|---|---|---|---|---|---|
| 1 | 整理-完成 | 再整理一次 | ✅ Tertiary | ✅ 合理 | 弱辅助操作，位于 Primary 之下、Ghost 之上，层级正确 |

**结论**：Tertiary 有真实且恰当的用途（完成页的次级再操作）。未滥用。

---

## 【Ghost Inventory】
| # | 页面 | 按钮 | 是否 Ghost | 是否合理 | 备注 |
|---|---|---|---|---|---|
| 1 | 顶栏 | 关于 | ✅ Ghost | ✅ 合理 | 极弱权重入口 |
| 2 | 历史页 | 返回首页 | ✅ Ghost | ✅ 合理 | 导航返回，弱 |
| 3 | 整理方案(离导航) | 返回首页 | ✅ Ghost | ✅ 合理 | 导航返回，弱 |
| 4 | 整理-完成 | 查看历史 | ✅ Ghost | ✅ 合理 | 低权重辅助 |
| 5 | 整理-完成 | 查看失败明细 | ✅ Ghost | ✅ 合理 | 默认隐藏，失败时出现 |
| 6 | 撤销确认弹窗 | 取消 | ✅ Ghost | ✅ 合理 | 弱操作，与「还原(undo-cta)」配对 |
| 7 | 预览报告弹窗 | 取消 | ✅ Ghost | ✅ 合理 | 弱操作，与「开始整理(primary)」配对 |

**结论**：Ghost **仅用于 取消/关闭/返回/低权重查看**，语义正确。

---

## 【Danger Inventory】
| # | 位置 | 按钮 | 是否 Danger | 备注 |
|---|---|---|---|---|
| — | 全项目 | （无） | ❌ 无实例 | Danger **当前 reserved** |

**结论**：全项目**无任何按钮使用 Danger**。Undo / 返回 / 取消 / 查看 / 普通辅助均**未**用 Danger。符合 §14「Danger 只保留给真正破坏性操作」。当前项目无真正破坏性操作 → `Danger currently reserved.` ✅

---

## 【Undo Inventory】（统一 Accent / Primary-Soft）
| # | 位置 | 可见文案 | objectName | 是否 undo-cta | 是否 Danger |
|---|---|---|---|---|---|
| 1 | 首页 | ♻️ 一键还原最近一次整理 | `undo-cta` | ✅ | ❌ |
| 2 | 整理-完成 | ♻️ 一键还原本次整理 | `undo-cta` | ✅ | ❌ |
| 3 | 历史页 | 撤销选中整理 | `undo-cta` | ✅ | ❌ |
| 4 | 撤销确认弹窗 | 还原 | `undo-cta` | ✅ | ❌ |

**结论**：所有用户可见 Undo 操作 **100% 统一为 `undo-cta`（Accent/Primary-Soft）**，**零 Danger** ✅。与 UI-1.2.2 裁决一致。

---

## 【发现问题】

### NO P0
- 无「一个页面多个 Primary 争夺焦点」的活跃页面。
- 无 Undo 用 Danger。
- 无 Primary 与 Ghost 倒挂（Ghost 比 Primary 更显眼）。
- 无未替换 token / 样式崩溃。

### NO P1
- 视觉权重链路 Primary > Secondary > Tertiary > Ghost 在所有活跃页面成立。
- Dialog 层级统一：弱(取消/Ghost) 在左/弱位，强(确认/还原/开始/undo-cta) 在右/主位。

### P2（轻微 / 可接受 / 建议后续阶段处理，本阶段不改）
- **P2-1** `custom_page.py` 同时存在 2 个 Primary（选择文件夹 + 开始整理）。
  - 归属：因 CustomPage 已在 Phase 2 从导航移除、仅保留注册（供 `test_appshell.py:67-69` 断言），属**离导航休眠页**；若「开始整理」在未选目录时 disabled，则实际仅 1 个可用 Primary。
  - 建议：UI 收尾后统一该页层级（选文件夹降为 Secondary，或确认其 disabled 逻辑），或随该页整体重构处理。
- **P2-2** `about.py:66` 「关闭」标为 Primary。
  - 单按钮弹窗，影响极小；但若追求 Windows 习惯，关闭类可改 Ghost。低优先级。
- **P2-3** `organize_page.py` 完成态按钮较密集（返回首页 primary + 一键还原 undo-cta + 再整理一次 tertiary + 查看历史 ghost + 查看失败明细 ghost）。
  - 实际可见 4 个（明细默认隐藏），且层级清晰（1 primary / 1 accent-soft / 1 tertiary / 2 ghost），符合「用户第一眼只需做一个决定」；记录为 **UI Complexity Note**，非缺陷。
- **P2-4** `preview_report.py` 使用两个独立 `QPushButton`（取消 ghost / 开始整理 primary），未显式设置默认按钮。
  - Windows 习惯建议：确保 **Enter = 开始整理（强）**、**Esc = 取消**。QDialog 默认 Esc 触发 `reject` ✅；但 Enter 默认激活首个控件（取消），可能与「强操作优先」相悖。
  - 建议：后续阶段显式 `ok_btn.setDefault(True)`。仅记录，本阶段不改。
- **P2-5** `organize_page.py:214` 完成页「返回首页」为 Primary，「一键还原」为 undo-cta。
  - 按 §8 设计意图：**返回首页应为第一焦点（Primary 正确）**，一键还原 accent-soft 次之且不可太弱——当前 solid accent > soft accent，层级正确。
  - 记录为**设计确认**：符合规范，无需修改。

---

## 【视觉层级结论】
**用户在每一个活跃页面都能一眼知道下一步吗？—— 能。**

- 首页：唯一 Primary「开始扫描」+ 次级「选择文件夹」+ accent-soft「一键还原」三者梯度清晰。
- 整理流程：配置态（选目录 secondary → 开始扫描 primary）→ 预览态（开始整理 primary）→ 完成态（返回首页 primary / 一键还原 accent-soft / 再整理 tertiary / 查看历史·明细 ghost），每一步下一步明确。
- Dialog：取消(弱) ↔ 确认/还原/开始(强)，无双强并列。
- Undo 全链路 accent-soft，从不与 Danger 混淆。

唯一需后续收尾的是 **P2-1 离导航页 + P2-4 默认按钮**，均非本阶段缺陷。

---

## 【Windows UX】（Tab / Enter / Esc / Focus / 按钮顺序，仅审计）
- **Tab 顺序**：按钮均为默认添加顺序，无显式 `setTabOrder`；Qt 按布局顺序遍历，合理。焦点态在 UI-1.2.2 已加全局 `:focus` 2px accent outline（克制、不位移）。✅
- **Enter**：QDialogButtonBox 弹窗（撤销确认）默认 Ok 为默认按钮 → Enter=还原（accent-soft 强操作），符合预期 ✅；`preview_report.py` 自定义双按钮未显式 `setDefault`（见 P2-4）。
- **Esc**：QDialog 默认 Esc=`reject`（取消）✅。
- **焦点环**：全局 `QPushButton:focus { outline: 2px solid {accent} }` 已覆盖所有变体 ✅。
- **按钮顺序**：确认类弹窗均为 [弱/左]→[强/右]，符合 Windows 桌面习惯 ✅。

**结论**：Windows 桌面交互习惯基本达标；仅 P2-4 一处默认按钮未显式化，建议后续阶段补齐。

---

## 【代码修改】
**NONE** —— 本报告为零代码改动只读审计。未触碰 `core/*`、`data/*`、`ui/undo.py`、`ui/state/worker.py`、`utils/*`，亦未改任何 UI 样式/布局文件。

## 【测试】
本阶段只读，按 §十九「不需要重新运行完整测试，可进行静态检查」。静态枚举已覆盖全部 `src/ui/**` 按钮定义（共 10 Primary / 2 Secondary / 1 Tertiary / 7 Ghost / 0 Danger / 4 undo-cta），与 UI-1.2.2 实施结果一致，无回归迹象。
> 基线（UI-1.2.2）：`compileall` PASS；`test_core/test_security/test_reliability/test_windows_paths/test_p2_coverage` 全 PASS。

## 【下一阶段】
**UI-1.2.4 — Tertiary / Ghost 复核**（按执行顺序）。但**不得自行进入**，等待确认。
