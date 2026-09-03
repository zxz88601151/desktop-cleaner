# Desktop Cleaner UI-1.3 — Migration Plan（迁移计划）

> 任务 §37–§39。本计划**待人工批准后**方可执行（当前为 READ-ONLY 审计阶段，未执行）。
> 核心路径（§37）：`New Design Tokens → New Components → Page-by-Page → Regression → Final UI`。**禁止删除全部 UI 重写**。

---

## 1. 范围与边界（RULE-0 延续到实施期）

- **只改 UI 表面层**：`src/ui/**`、`src/version.py` 文案、新增 `src/ui/icons.py`。
- **不动**：`core/`、`data/`、`utils/`、整理算法、DB 结构、撤销逻辑、测试断言逻辑、构建脚本。
- **不影响已发布 V1.1.0**：UI-1.3 属后续版本，独立提交/打 tag。

---

## 2. 阶段划分（推荐 5 阶段，P0/P1/P2）

### Phase 1 — 图标系统 + 命名 + 文案（P0/P1，最高杠杆）
**改动**：
- 新增 `src/ui/icons.py`：QPainter 线型图标集（零依赖），替换全站 emoji。
- 全局替换"智能整理"→"整理"（sidebar/app_shell/organize_page/history 空状态文案）。
- 改 `custom_page.py:90` "让数字空间焕然一新"→"选择整理方式，整理前可预览"。
- 去按钮/完成/撤销/关于/主题中的 emoji（♻️✅🌙☀️📂…）。
- 全站 emoji 图标 → `IconSet` 映射（导航/统计/分类/历史行/关于/Coming Soon 移除后）。

**文件**：`icons.py`(新) / `sidebar.py` / `app_shell.py` / `organize_page.py` / `history_page.py` / `dashboard.py` / `custom_page.py` / `about.py` / `undo.py` / `dashboard_page.py` / `preview_report.py` / `features.py` / `coming_soon.py`(随 Phase 3)。

**回归**：11+ 测试套件全 PASS（不改断言逻辑）。

### Phase 2 — Design Tokens（P1）
**改动**：
- `themes.py`：accent `#4F46E5`→`#2B6CB0`（深 `#818CF8`→`#6CA0DC`）；radius 14/10/8→8/6/4；删除 `shadow` 用法。
- `dashboard.py`：移除 `QGraphicsDropShadowEffect`（StatCard 去投影）。
- 徽章/胶囊 `999px`→4–6px。

**回归**：headless 渲染 light/dark 无未替换 token；compileall PASS。

### Phase 3 — 移除概念预告页（P1）
**改动**：
- `sidebar.py`：从 `_NAV` 移除 `tools` 项；`_TITLES` 移除 `tools`/`custom`(按 Phase 方案)。
- `app_shell.py`：移除 `ToolsPage` 注册与 `dashboard_page` 的"发现更多工具 →"入口。
- `coming_soon.py` / `tools_page.py`：从导航不可达（模块可暂留以免破坏测试；后续版本可删）。
- `custom_page`（整理方案）：**接回**为"整理方式"入口（方案 A 加回导航 / 方案 B 并入 organize 的 Segmented）—— 解决孤儿页 + 模式选择可达性。

**回归**：`test_appshell.py` 对 `CustomPage` 存在的断言 — 若方案 B 删除模块需同步改测试（属测试契约调整，非降断言）。

### Phase 4 — 首页去圆环 + Hero 强化（P1/P2）
**改动**：
- `dashboard_page.py`：移除 `ScoreRing` 整洁度角落（`compute_clean_score` 可保留供内部，但不展示大圆环/56px 数字）；强化文件夹优先 Hero；"最近整理"摘要保留（真实历史）。
- `score_ring.py`：保留控件，仅用于 organize 执行态真实进度环，不作整洁度。

**回归**：headless 校验首页无圆环、文件夹为第一焦点。

### Phase 5 — 全量回归 + 像素走查（P2）
- 11+ 套测试全 PASS；clean build；offscreen 启动冒烟；如有无显示服务器则截图走查（否则声明限制）。
- 无障碍抽查：Tab/Focus/Tooltip/对比度。

---

## 3. 优先级汇总（§39 Q18）

| 优先级 | 项 |
|---|---|
| **P0** | 图标系统替换 emoji（去 AI 味最核心） |
| **P1** | 命名"智能整理"→"整理"；文案去营销；accent 去蓝紫；降圆角；去卡片投影；移除"更多工具"/Coming Soon；接回模式选择；首页去圆环 |
| **P2** | 徽章圆角收敛；关于去 emoji；像素走查；无障碍补强 |

---

## 4. 对 V1.1.0 / 测试 / 功能的影响（§39 Q14–16）

| 项 | 影响 |
|---|---|
| **V1.1.0** | **无**。已发布 tag `v1.1.0` + Gitea Release 不受影响；UI-1.3 独立后续版本。 |
| **功能** | **无**。整理/预览/撤销/历史/设置行为不变；仅改名与换图标。 |
| **测试** | 11+ 套全 PASS（断言逻辑不改）。唯一风险：`test_appshell` 对 `CustomPage` 存在的断言——Phase 3 若删 `custom_page` 模块需同步调整该测试（调整契约，非伪造/降断言）。 |
| **构建** | `build.spec` 无需改（icons 走代码绘制，零新依赖）。 |

---

## 5. 风险与回滚

| 风险 | 缓解 |
|---|---|
| 线型图标绘制工作量 | 先覆盖高频语义图标（home/organize/history/settings/folder/undo/check/type/date），分类可先用纯文字标签兜底 |
| emoji 散落多处遗漏 | Phase 1 用 Grep `[\x{1F000}-\x{1FAFF}\x{2600}-\x{27BF}]` 全仓扫描确认清零 |
| 改 `custom_page` 破坏测试 | Phase 3 先跑 `test_appshell` 再决定方案 A/B |
| 配色主观 | accent 提案 `#2B6CB0` 可作变量，实施期由你最终拍板 |

---

## 6. 验收标准（Final Gate）

- [ ] 全站零 emoji（Grep 清零）
- [ ] 无"智能/AI/魔法/焕然一新"类文案
- [ ] 导航仅任务词（整理/历史/设置），无概念预告页
- [ ] Accent 非蓝紫、圆角 ≤8px、卡片无投影
- [ ] 首页第一焦点 = 文件夹 + 扫描；无整洁度大圆环
- [ ] 预览确认 / 撤销确认 保持范本质量
- [ ] 11+ 测试全 PASS；clean build；offscreen 冒烟 PASS
- [ ] 已发布 V1.1.0 不受影响

---

## 7. 最终判断（§40）
**B. REFACTOR UI**。信息架构与核心流程成熟，去味聚焦表面层（图标/命名/配色/圆角/概念页/圆环），无需推倒重来，无需改动业务层。

---
*本文件为 READ-ONLY 审计的后续实施计划草案，当前未执行任何代码改动。*
