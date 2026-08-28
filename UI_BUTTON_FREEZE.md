# Desktop Cleaner — Button System Freeze（按钮体系冻结声明）

**冻结时间**：2026-08-28  
**冻结阶段**：UI-1.2.8 Button System Final Freeze  
**审计链**：UI-1.2.1 → UI-1.2.2 → UI-1.2.3 → UI-1.2.4 → UI-1.2.5 → UI-1.2.6 → UI-1.2.7 → **UI-1.2.8**  
**状态**：🔒 **BUTTON SYSTEM = FROZEN**

---

## 1. 冻结含义

自本声明起，**Button 体系进入冻结状态**：

1. 未经显式「Button 重新审计」流程，不得修改 `src/ui/theme/themes.py` 中任何 `QPushButton` / `#primary` / `#secondary` / `#tertiary` / `#ghost` / `#danger` / `#icon` / `#undo-cta` / `#nav-item` / `#seg` 相关 QSS 规则。
2. 不得修改任何 UI 文件中按钮的 `setObjectName()` 变体指定、CTA 文案、Dialog 按钮层级（Ghost 左 / Primary·Undo 右）、`setDefault()` 默认按钮配置。
3. 产品语义锁定：**撤销 / 一键还原 = Accent-Soft（`undo-cta`），绝不是 Danger**。
4. 层级锁定：**Primary > Secondary > Tertiary > Ghost**；Secondary 仅用于「选择文件夹」；Ghost 仅用于取消/返回/低权重查看。

> 注：本冻结是 UI-1 Design System 的子系统冻结。全局 `UI_FREEZE.md`（2026-08-28）仍然有效；Button 冻结为其在 UI-1.2 阶段的细化锁定。

---

## 2. 冻结范围（已审计并锁定）

### 变体清单（实例数 · 2026-08-28 静态枚举）

| 变体 | 实例 | 用途 |
|------|------|------|
| `primary` | 10 | 页面/弹窗唯一主 CTA |
| `secondary` | 2 | 「选择文件夹」次级动作 |
| `tertiary` | 1 | 完成页「再整理一次」 |
| `ghost` | 7 | 取消 / 返回 / 低权重查看 |
| `undo-cta` | 4 | 全部撤销入口（Accent-Soft） |
| `icon` | 1 | 主题切换（有 Tooltip） |
| `nav-item` | 4 | Sidebar 导航 |
| `seg-btn` | 4 | Segmented 模式切换 |
| `danger` | 0 | **预留**，禁止用于撤销 |

### 已锁定的交互行为

- 全局 `:focus` 焦点环（2px accent outline，无布局位移）
- Preview / Welcome / About 的 `setDefault(True)` 默认按钮
- Undo Dialog QDialogButtonBox Ok = default
- 4 Dialog Esc/X → reject，不误触强操作

### 已清理

- `#link`（死样式，已删）
- `#undo-done`（danger 红撤销，已删）

---

## 3. 明确禁止（冻结期内）

- ❌ 将任何撤销按钮改回 `danger` 或红色语义
- ❌ 新增第二套 Button QSS 模板或平行 token 体系
- ❌ 为「好看」引入缩放/跳动/动画类 pressed 反馈
- ❌ 在活跃页放置 2+ 个同等级 Primary 争夺焦点
- ❌ 用「确认 / 确定 / OK / 执行 / 继续」替代已锁定的 CTA 文案
- ❌ 在未重新审计的情况下修改 Dialog 按钮左右顺序或 Esc 行为

---

## 4. 已知 P2（已接受，不触发解冻）

1. `#undo-cta` 无专属 `:pressed`（继承 generic）
2. `#ghost-link` QSS 存在但零实例
3. CustomPage（离导航）2 Primary 并列
4. About 单按钮 = Primary
5. Tertiary vs Ghost idle 视觉近似

以上归 **UI-1.3 Typography / Spacing** 或后续清理，**不构成 Button 体系缺陷**。

---

## 5. 解冻流程

1. 提出变更原因与影响面（直接影响 → 间接影响 → Dialog 安全 → 测试）。
2. 创建增量审计快照（如 `UI_BUTTON_BASELINE.md`）。
3. 实施 → `compileall` + 5 套核心测试 → headless 变体渲染校验。
4. 更新 `UI_1_2_8_Button_System_Final_Freeze.md` 或新建子阶段报告 → 重新签署本声明。

---

## 6. 下一阶段

**UI-1.3 — Design System**（Card / Typography / Spacing / Empty / Loading / Error / Toast / Progress / List / Badge / Status）

Button System 已收官。停止在 Button 上无限迭代。
