# UI-1.2.5 — Danger / Undo Semantic Review

## 1. 阶段
UI-1.2.5（Button Semantic Final Review，UI-1.2 子阶段 5/8）

## 2. 修改文件
NONE（本阶段未发现任何语义错误，依 §XI 仅"发现明确语义错误时"才允许最小修改，故零改动）

## 3. Undo 审计
- Dashboard 一键还原：`dashboard_page.py:157` → `undo-cta` ✅ PASS
- Organize 完成页 一键还原本次整理：`organize_page.py:210` → `undo-cta` ✅ PASS
- History 撤销选中整理：`history_page.py:154` → `undo-cta` ✅ PASS
- Undo Confirmation Dialog 还原：`ui/undo.py:114` → `undo-cta` ✅ PASS

全链路结论：**Undo = Accent / Primary-Soft（undo-cta）一致，零 Danger。**

## 4. Danger 审计
Danger 使用数量（按钮实例）：**0**

全 `src/` 静态检索结果：
- 无任何 `setObjectName("danger")` 按钮实例化。
- `src/ui/theme/themes.py` 中 `#danger` QSS（170–180 行）与 `danger` / `danger_hover` / `danger_soft` token 仅为**预留样式定义**，非活跃按钮。
- `#report-warn`（`themes.py:360`，color={danger}）与 `#tl-tag[state="failed"]`（`themes.py:475`）为**信息性提示色**（"文件不会删除，可随时撤销" / 失败状态标签），非破坏性按钮，语义正确。
- 业务文案中的"删除/移除"均为说明性文字（errors.py、welcome.py、preview_report.py 等），无对应 Danger 按钮。

结论：**PASS**
V1.0 当前不存在永久删除 / 清空历史 / 清空全部记录 / 删除不可恢复数据 / 删除重要配置 / 重置全部设置等不可逆功能，Danger = 0 是合规状态，而非"缺少 Danger"。红色未因"看起来醒目"被滥用。

## 5. Dialog 审计
| Dialog | 弱化/左 | 强/右 | 结论 |
|---|---|---|---|
| Undo 确认（undo.py） | 取消 = Ghost（117） | 还原 = Undo CTA（114） | ✅ PASS |
| Preview Report（preview_report.py） | 取消 = Ghost（122） | 开始整理 = Primary（125） | ✅ PASS |
| Welcome（单按钮） | — | 开始使用 = Primary（81） | ✅ PASS |
| About（单按钮） | — | 关闭 = Primary（66） | ⚠️ Accepted Note（见 §7） |

统一规则已落地：取消/返回 = Ghost（弱·左），确认/开始/还原 = Primary 或 Undo CTA（强·右）。无"取消 = Danger 还原"等反模式。

## 6. Semantic Violations
NONE

检索 `undo+danger` / `restore+danger` / `还原+danger` / `撤销+danger` 组合：全项目 0 处。
Primary ≠ Danger、Undo ≠ Danger、Cancel ≠ Danger、Back ≠ Danger 均成立。

## 7. P2 Notes
- **P2-1（preview_report.py Enter 默认键）**：`ok_btn`（开始整理，Primary）未显式 `setDefault(True)`，当前 Enter 可能不指向「开始整理」。建议后续阶段加 `ok_btn.setDefault(True)`（UI-1.2.6 / UI-1.2.8 范围）。本阶段依 §VII 只记录、不扩大修改。
- **Accepted Note — About 单按钮「关闭」= Primary**：单按钮弹窗，唯一操作即关闭，符合 §八"单按钮 Dialog 可接受 Primary"，记录为 Accepted，不强行改为 Ghost。
- **Dormant Note — custom_page.py（离导航休眠页）**：browse/start 均为 Primary，但页面已移出导航，不影响活跃流程语义，沿用 UI-1.2.3 记录的 Dormant UI Note，本阶段不处理。

## 8. 测试
compileall: PASS
test_core: PASS
test_security: PASS
test_reliability: PASS
test_windows_paths: PASS
test_p2_coverage: PASS

（本阶段零代码改动，以上为 UI-1.2.2 基线 + 本次复跑双重确认）

## 9. 风险
- 极低。本次为纯只读语义审计，未触碰任何文件，未改禁改区（core/*、data/*、ui/undo.py 业务逻辑、ui/state/worker.py、utils/*）。
- 唯一待办 P2-1（Enter 默认键）属交互增强，非语义错误，归 UI-1.2.6/UI-1.2.8 处理。

## 10. 下一阶段
UI-1.2.6 — Focus / Pressed / Keyboard Interaction Final Review

等待确认，不得自动进入下一阶段。
