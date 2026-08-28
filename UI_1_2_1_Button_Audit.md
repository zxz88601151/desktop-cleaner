# UI-1.2.1 — Existing Button Audit（只读审计，未改代码）

> UI-1.2 子阶段 1/8。本阶段**只审计现有 Button 体系**，不修改任何代码、不进后续 UI-1.2.2+。

---

## 【阶段】
UI-1.2.1 / Existing Button Audit（UI-1.2 子阶段 1 / 8）

## 【修改文件】
无（只读审计）。

## 【修改内容】
无。

## 【未修改内容】
- `src/ui/theme/themes.py` 及所有 `src/ui/**` 按钮使用点均未改动。
- 禁改区（`core/*`、`data/*`、`ui/undo.py`、`ui/state/worker.py`、`utils/*`）未动。
- 未创建 `#tertiary`、未加 `:focus`、未统一 Disabled/Dialog/首页 CTA —— 这些归 UI-1.2.2~UI-1.2.6。

## 【测试结果】
无代码改动，不重跑。UI-1.1 基线：5 套测试（`test_core/security/reliability/windows_paths/p2_coverage`）+ `compileall -q src main.py` 全 PASS，本阶段保持。

## 【UI 验证】
静态枚举 + QSS 状态覆盖矩阵（见下）。无像素级渲染（headless 无法目检），结论基于源码取证。

## 【风险】
无（只读）。

## 【下一阶段】
UI-1.2.2 Button Token / Style：基于本审计，补齐 `#tertiary`、为所有变体加 `:focus`、补齐 `ghost`/`icon` 的 `:pressed`、清理/复用死样式 `#link`、统一 `undo` 语义按钮层级、给 `preview_report.cancel_btn` 明确变体。完成后停止并汇报。

---

## 一、当前 Button 变体清单（QSS 定义）

定义位于 `src/ui/theme/themes.py`（单一 `QSS_TEMPLATE`，双主题 token 替换）。现有 6 类 QPushButton 样式 + 3 类特例：

| QSS 选择器 | 语义档 | normal | hover | pressed | disabled | focus |
|-----------|--------|--------|-------|---------|----------|-------|
| `QPushButton`（generic） | 默认中性 | ✓ | ✓(surface_hover) | ✓(surface_alt) | ✓ | ✗ |
| `#primary` | Primary | ✓ | ✓ | ✓(accent_pressed) | 通用 disabled | ✗ |
| `#secondary` | Secondary | ✓ | ✓ | ✓(border) | 通用 disabled | ✗ |
| `#danger` | Danger | ✓ | ✓ | ✓(danger_soft) | 通用 disabled | ✗ |
| `#ghost` | Ghost | ✓ | ✓ | **✗ 缺失** | 通用 disabled | ✗ |
| `#icon` | Icon（方按钮） | ✓ | ✓ | **✗ 缺失** | 通用 disabled | ✗ |
| `#link` | Link | ✓ | ✓ | — | — | ✗（**且全项目无实例化 = 死样式**） |
| `#ghost-link` | 链接式 Ghost | ✓ | ✓ | — | — | ✗（organize 用） |
| `#undo-cta` | 撤销 CTA（accent 软） | ✓ | ✓ | — | — | ✗（dashboard 用） |
| `#undo-done` | 还原按钮（danger 红） | ✓ | ✓ | — | — | ✗（organize 用） |
| `#nav-item` | 导航按钮（自定义） | ✓ | ✓ | — | — | ✗（sidebar 用，归 UI-1.6） |
| `#seg QPushButton` | 分段控件按钮 | ✓ | ✓ | — | — | ✗（settings 用） |

**结论**：标准 6 档中，**`#tertiary` 完全缺失**；`Primary/Secondary/Danger` 五态齐全；`Ghost/Icon/#link/#ghost-link/#undo-*` 缺 `:pressed`；**全部变体缺 `:focus`**；`Disabled` 仅由通用 `QPushButton:disabled` 兜底（可读，但未做"逐变体"精修）。

## 二、Button 实例化盘点（按页面）

| 位置 | 文本 | 当前档 | 备注 |
|------|------|--------|------|
| dashboard_page | 选择文件夹 | `#secondary` | ✓ |
| dashboard_page | 开始扫描 | `#primary` | 首页唯一主 CTA ✓ |
| dashboard_page | ♻️ 一键还原最近一次整理 | `#undo-cta` | accent 软，非 danger |
| organize_page | 选择文件夹 | `#secondary` | ✓ |
| organize_page | 开始扫描 | `#primary` | ✓ |
| organize_page | 开始整理 | `#primary` | ✓ |
| organize_page | ♻️ 一键还原本次整理 | `#undo-done` | **danger 红**（与 dashboard 的 undo-cta 不一致） |
| organize_page | 返回首页 | `#primary` | ⚠ 可降级为 ghost/secondary |
| organize_page | 查看历史 | `#ghost` | ✓ |
| organize_page | 再整理一次 | `#ghost` | ✓ |
| organize_page | 查看失败明细 | `#ghost-link` | ✓ |
| history_page | 撤销选中整理 | `#secondary` | P1-4 已从 danger 改为 secondary |
| history_page | 返回首页 | `#ghost` | ✓ |
| preview_report | 取消 | **（generic，无 objectName）** | ⚠ 未明确变体，应 secondary/ghost |
| preview_report | 开始整理 | `#primary` | ✓ |
| about | 关闭 | `#primary` | ⚠ 关闭类宜 ghost/secondary |
| welcome | 开始使用 | `#primary` | ✓ 首启唯一主 CTA |
| app_shell | 关于 | `#ghost` | ✓ |
| app_shell | 主题切换 | `#icon` | ✓ |
| undo.ConfirmUndoDialog | 还原 | `#danger` | ✓ 确认弹窗用 danger |
| undo.ConfirmUndoDialog | 取消 | generic（QDialogButtonBox） | ⚠ 未明确变体 |
| custom_page | 选择文件夹 / 开始整理 | `#primary`×2 | ⚠ 两个 Primary（该页不可达，但样式需规范） |
| custom_page | 返回首页 | `#ghost` | ✓ |
| settings_page | 关于本软件 | `#primary` | ✓ |
| sidebar | 4× 导航 | `#nav-item` | 导航按钮，归 UI-1.6 |
| controls.SegmentedControl | 分段选项 | `#seg QPushButton` | 自定义 |

## 三、关键发现（Gap → 后续子阶段归属）

1. **缺 `#tertiary`**（UI-1.2.4 重点）：高级设置/查看全部/弱辅助操作无对应档。当前这类操作被塞进 `#ghost` 或 `#link`，层级语义不清。
2. **全变体缺 `:focus`**（UI-1.2.6 重点）：键盘可达性无可见但克制的焦点环，违反 §10。需基于 token 加 `outline`/边框反馈，不破坏布局。
3. **`ghost` / `icon` 缺 `:pressed`**（UI-1.2.6）：pressed 反馈缺失，点击无"按下"感。
4. **`undo` 语义按钮层级不统一**（UI-1.2.5 待决）：
   - dashboard「一键还原」= `#undo-cta`（accent，不红）
   - organize「一键还原本次整理」= `#undo-done`（danger 红）
   - history「撤销选中整理」= `#secondary`（P1-4 去红）
   - confirm 弹窗「还原」= `#danger`
   → 撤销动作在四处的视觉语言冲突。需决策：撤销到底用 Danger 还是 Acsent/secondary（§8 说撤销用 Danger，但 §15/P1-4 怕误伤）。**本审计只记录，不决议。**
5. **`preview_report.cancel_btn` 与 `undo` 取消按钮无变体**（UI-1.2.5/UI-1.2.7）：用 generic QPushButton，应明确为 `secondary` 或 `ghost`，Dialog 按钮排列统一（§17：取消弱/左，确认强/右）。
6. **`#link` QSS 死样式**（UI-1.2.2 清理）：全项目无 `setObjectName("link")`，可删除或并入 `#ghost-link`，避免维护第二套链接样式。
7. **首页主 CTA 层级**（§15）：当前 dashboard 仅一个 `#primary`（开始扫描）+ 一个 `#secondary`（选择文件夹），层级正确；organize 完成页「返回首页」用了 `#primary`，建议降级。custom_page（不可达）有两个 primary，仅规范隐患。
8. **统一尺寸**（§12）：现有按钮 padding 不统一（`QPushButton` 8px 18px；`#icon` 6px 10px；`#link` 2px 4px；各 `#xxx` 内部 8~18px）。`#primary/#secondary/#ghost/#danger` 共用 `QPushButton` 的 `padding:8px 18px` + `font-size:13px`，主尺寸已统一为 Medium，无需再造 Small/Large（符合"实际使用优先"）。
9. **统一圆角**（§13）：所有按钮 `border-radius: {radius_xs}`（8px），已统一，✓ 无页面差异。

## 四、状态覆盖矩阵（目标 vs 现状）

| 变体 | normal | hover | pressed | disabled | focus |
|------|--------|-------|---------|----------|-------|
| Primary | ✓ | ✓ | ✓ | ✓(通用) | ✗ |
| Secondary | ✓ | ✓ | ✓ | ✓(通用) | ✗ |
| Tertiary | **✗ 缺失** | **✗** | **✗** | **✗** | **✗** |
| Ghost | ✓ | ✓ | ✗ | ✓(通用) | ✗ |
| Danger | ✓ | ✓ | ✓ | ✓(通用) | ✗ |
| Disabled(态) | — | — | — | ✓(通用兜底) | — |

## 五、Light / Dark 验证状态

所有现有变体颜色均来自 `LIGHT`/`DARK` 调色板 token（`accent`/`on_accent`/`surface_*`/`text_*`/`danger`/`danger_soft`），`build_stylesheet(theme)` 双主题替换，UI-1.1 已校验无未替换 token。故 Light/Dark 在**现有变体**上一致；`#tertiary` 与 `:focus` 补全后须在 UI-1.2.7 复验双主题。

---

### 审计结论
现有 Button 体系**地基可用但缺三块**：① 无 `#tertiary`；② 全变体无 `:focus`；③ `ghost`/`icon` 无 `:pressed`；外加 `undo` 语义按钮四处分歧、`cancel_btn` 无变体、`#link` 死样式。这些全部归 UI-1.2.2~UI-1.2.6 修复，**本阶段不改代码**。
