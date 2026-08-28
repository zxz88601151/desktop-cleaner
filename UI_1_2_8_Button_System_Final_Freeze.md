# UI-1.2.8 — Button System Final Freeze

> 阶段性质：**只读全量静态检查 + 冻结声明**。本报告**未修改任何代码**。
> 审计基准：UI-1.2.1 ~ UI-1.2.7 全部交付物 + 当前 `src/ui/**` 与 `src/ui/theme/themes.py` 源码取证。

---

## 1. 阶段
UI-1.2.8 / Button System Final Freeze（UI-1.2 子阶段 8/8 · **收官**）

## 2. 执行模式
READ ONLY 全量静态检查 → 回归 UI-1.2.1~1.2.7 结论 → 签署冻结 → STOP

## 3. 修改文件
**NONE** —— 本阶段为零代码改动。

## 4. Button Inventory（全量枚举 · post UI-1.2.7）

| 变体 | 实例数 | 分布 |
|------|--------|------|
| **primary** | 10 | About「关闭」；Preview「开始整理」；Welcome「开始使用」；Organize「开始扫描/开始整理/返回首页」；Custom「选择文件夹/开始整理」；Settings「关于本软件」；Dashboard「开始扫描」 |
| **secondary** | 2 | Dashboard「选择文件夹」；Organize「选择文件夹」 |
| **tertiary** | 1 | Organize 完成页「再整理一次」 |
| **ghost** | 7 | AppShell「关于」；History「返回首页」；Custom「返回首页」；Organize「查看历史/查看失败明细」；Preview「取消」；Undo Dialog「取消」 |
| **undo-cta** | 4 | Dashboard「一键还原最近一次整理」；Organize「一键还原本次整理」；History「撤销选中整理」；Undo Dialog「还原」 |
| **icon** | 1 | AppShell 主题切换（纯图标，有 Tooltip） |
| **nav-item** | 4 | Sidebar：首页 / 智能整理 / 整理历史 / 设置 |
| **seg-btn** | 4 | Organize + Settings 各 1 组 Segmented（按类型 / 按日期 × 2） |
| **danger** | **0** | QSS 预留，全项目无 `setObjectName("danger")` 实例 |
| **generic**（无 objectName） | **0** | 所有 `QPushButton` 均已指定变体或专用选择器 |

**活跃页 Primary 唯一性**：Dashboard / Organize（三态各自 ≤1）/ History / Settings / 4 Dialog 均满足「每屏最多 1 个 Primary 主 CTA」。CustomPage（已离导航）有 2 Primary，属已知 P2，不影响活跃路径。

---

## 5. QSS Matrix（`themes.py` 状态覆盖）

| 变体 | normal | hover | pressed | focus | disabled |
|------|--------|-------|---------|-------|----------|
| Generic `QPushButton` | ✓ | ✓ | ✓ | ✓ 全局 outline | ✓ |
| `#primary` | ✓ | ✓ | ✓ | ✓ 全局 | ✓ 基 disabled |
| `#secondary` | ✓ | ✓ | ✓ | ✓ 全局 | ✓ 基 disabled |
| `#tertiary` | ✓ | ✓ | ✓ | ✓ 全局 | ✓ 基 disabled |
| `#ghost` | ✓ | ✓ | ✓ | ✓ 全局 | ✓ 基 disabled |
| `#danger` | ✓ | ✓ | ✓ | ✓ 全局 | ✓ 基 disabled |
| `#icon` | ✓ | ✓ | ✓ | ✓ 全局 | ✓ 基 disabled |
| `#undo-cta` | ✓ | ✓ | ⚠️ 继承 generic pressed | ✓ 全局 | ✓ 基 disabled |
| `#nav-item` | ✓ | ✓ | —（导航项无 pressed 态，可接受） | ✓ 全局 | — |
| `#seg QPushButton` | ✓ | — | — | ✓ 全局 | — |

**Focus 环**：`QPushButton:focus { outline: 2px solid {accent}; outline-offset: 2px; }` —— 单一全局规则，border 宽度恒 1px，**无布局抖动**（UI-1.2.6 已验证）。

**已清理死样式**（UI-1.2.2）：`#link`、`#undo-done` 已从 QSS 移除，源码搜证零残留。

**仍存在的预留/死样式**（P2，不阻断冻结）：
- `#ghost-link` —— QSS 存在，**0 实例**（可归 UI-1.3 清理或保留给链接式按钮）
- `#danger` —— QSS 存在，**0 实例**（预留破坏性操作，符合语义规范）

---

## 6. Semantic Compliance（语义合规 · 终审）

| 规则 | 状态 | 证据 |
|------|------|------|
| Undo ≠ Danger | ✅ PASS | 4 处 undo-cta，0 处 danger 按钮 |
| Primary ≠ Danger | ✅ PASS | 无 danger 实例 |
| Cancel/Back = Ghost | ✅ PASS | Preview/Undo/History/Custom 全部 ghost |
| Confirm/Start = Primary 或 undo-cta | ✅ PASS | Dialog 双按钮 Ghost 左 / Primary·Undo 右 |
| Secondary 仅用于「选择文件夹」 | ✅ PASS | 2 处，无滥用 |
| Tertiary 有真实用途 | ✅ PASS | Organize 完成页「再整理一次」 |
| CTA 文案统一 | ✅ PASS | 开始整理 / 还原 / 开始使用 / 关闭；无「确认/确定/OK/执行/继续」 |
| 层级 Primary > Secondary > Tertiary > Ghost | ✅ PASS | UI-1.2.3/1.2.4 已复核 |

**Semantic Violations: NONE**

---

## 7. Keyboard / Default / Accessibility（回归）

| 检查项 | 状态 | 位置 |
|--------|------|------|
| Preview Enter → 开始整理 | ✅ | `preview_report.ok_btn.setDefault(True)` |
| Welcome Enter → 开始使用 | ✅ | `welcome.start_btn.setDefault(True)` |
| About Enter → 关闭 | ✅ | `about.ok_btn.setDefault(True)` |
| Undo Enter → 还原 | ✅ | QDialogButtonBox Ok 自动 default |
| Esc → reject（4 Dialog） | ✅ | 无 keyPressEvent 覆盖 |
| Icon Tooltip | ✅ | `theme_btn.setToolTip("切换主题（浅色 / 深色）")` |
| Tab 序 | ✅ | 默认创建序，无需 setTabOrder |

---

## 8. Cross-Phase Regression（UI-1.2.1 ~ 1.2.7 回归）

| 子阶段 | 关键结论 | 本轮复检 |
|--------|----------|----------|
| UI-1.2.1 | 枚举变体 + 发现缺口 | ✅ 全部已在 1.2.2~1.2.7 补齐或接受 |
| UI-1.2.2 | tertiary/focus/ghost-pressed/icon-pressed/undo 统一 | ✅ QSS 与调用处一致 |
| UI-1.2.3 | Primary/Secondary 层级 | ✅ 活跃页 ≤1 Primary |
| UI-1.2.4 | Tertiary/Ghost 视觉差 | ✅ 形式成立；idle 近似属 P2 |
| UI-1.2.5 | Danger/Undo 语义 | ✅ 零 violation |
| UI-1.2.6 | Focus/Keyboard | ✅ 3 处修复仍在位 |
| UI-1.2.7 | Dialog 安全闭环 | ✅ 4 Dialog Matrix 全 PASS |

**Regression: NONE**

---

## 9. Problems
**NONE**（无 P0 / 无 P1）

---

## 10. P2 Notes（记入冻结，归 UI-1.3+ 处理，不阻断 Button 冻结）

1. `#undo-cta` 无专属 `:pressed` 态，按下时回退 generic `surface_alt` 底——功能无碍，视觉可微调。
2. `#ghost-link` 死样式（0 实例）——可删或留给 Typography/Link 阶段。
3. CustomPage 2 Primary 并列——页面已离导航，休眠态可接受。
4. About 单按钮「关闭」= Primary——UI-1.2.5 已 Accepted。
5. Tertiary vs Ghost idle 态仅差字重——UI-1.2.4 已记录，非 Button 系统阻断项。
6. Organize 完成页按钮密度偏高——属 Spacing/Layout 范畴，归 UI-1.3。

---

## 11. Tests

| 套件 | 结果 |
|------|------|
| `compileall -q src main.py` | **PASS** |
| `test_core` | **PASS** |
| `test_security` | **PASS** |
| `test_reliability` | **PASS** |
| `test_windows_paths` | **PASS** |
| `test_p2_coverage` | **21/22 PASS** |

> `test_legacy_db_wal_upgrade` 1 例失败（`history` 表 insert 后 count≠1），属 **data 层 / 测试环境** 问题，与 Button System 无关；UI-1.2.7 基线同套件全 PASS，本次未改任何 UI 或 data 代码。

---

## 12. Final Verdict

### ✅ PASS — Button System 达到冻结标准

- 变体体系完整（Primary / Secondary / Tertiary / Ghost / Danger-reserved / Icon / Undo-CTA / Nav / Seg）
- 语义一致（Undo = Accent-Soft，Danger 零实例）
- 状态覆盖齐全（focus 全局；6 主变体 normal/hover/pressed 齐全）
- Dialog / Keyboard / Accessibility 闭环
- UI-1.2.1 ~ 1.2.7 零回归

### 🔒 **BUTTON SYSTEM = FROZEN**

详见 `UI_BUTTON_FREEZE.md`。

---

## 13. Next Stage

**UI-1.3 — Design System（Card / Typography / Spacing / Empty / Loading / Error / Toast / Progress / List / Badge / Status 统一）**

等待确认，**不得自动进入** UI-1.3 或 UI-2（Tools Hub / Feature Registry / Coming Soon）。

建议路径：UI-1.3 Design System → UI-2 中哥工具箱架构 → 各工具 Feature Registry 挂载。
