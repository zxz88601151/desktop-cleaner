# Desktop Cleaner — UI Freeze (冻结声明)

**冻结时间**：2026-08-28
**冻结版本**：`dist/DesktopCleaner.exe`（v1.1.0，SHA-256 `6f840365b5bf96b1faa6ba301b1703c61af1293932baeb678668dc2583a9a75e`）
**状态**：🔒 **UI = FROZEN**

---

## 1. 冻结含义

自本声明起，**UI 层（全部 `src/ui/` 目录）进入冻结状态**：

1. 未经显式「UI 重新审计」流程，不得修改任何 UI 组件、布局、配色、字体、间距、圆角、图标、QSS token 或交互文案。
2. 业务层（`core/`、`data/`、`utils/`）的改动若**不影响既有 UI 契约**（如 `PlanItem.category`、`OrganizeResult.items` 字段名、对话框信号、导航页 id），不触发本冻结。
3. 若业务层变更**会**改变 UI 契约（字段重命名、信号增删、页面 id 调整、新增分类），必须先解冻 → 重新审计 → 再冻结。

---

## 2. 冻结范围（已审计并锁定）

### 已交付的 P0 / P1 / P2 项（见 `UI_FINAL_AUDIT.md` §2）
- P0：首页 Hero 重构（选择文件夹→扫描→预览 为第一焦点；整洁度降权为角标）
- P1：按钮三级层级(`#secondary`)、扫描→一步确认、预览卡片化+扩展名提示、History 撤销去红、导航收敛、最小尺寸 900×620、硬编码样式收口到 token
- P2：署名 © 中哥、欢迎页 +2 要点、History 相对时间+源路径、高 DPI、完成页分类统计、时段问候

### 保持不变的既有设计
- token 化 QSS 体系（`ui/theme/themes.py` 单一模板 + `{token}` 替换）
- 三主题无关结构；`ThemeManager` 单例
- 错误友好化（`Worker` 吞栈、对话框确认）
- 时间线式 History、非伪造无死亡态

---

## 3. 明确禁止（冻结期内）

- ❌ 引入玻璃拟态 / 大渐变 / 花哨动画
- ❌ 修改 `CATEGORY_NAMES` / `category_emoji` 等 core 显示常量（如需新增分类，先解冻并改 core + 同步 UI）
- ❌ 新增 UI 框架 / WebView / React-Vue / 新第三方 UI 库
- ❌ 为「好看」而改业务行为
- ❌ 在未重新审计的情况下删改已冻结的测试契约（尤其 `test_appshell` 对 `custom` 页面的注册断言）

---

## 4. 解冻流程

1. 提出变更原因与影响面分析（直接影响→间接影响→数据→API→UI→测试）。
2. 创建 `UI_BASELINE.md` 增量快照 + 更新 `UI_REFINEMENT_PLAN.md`。
3. 实施 → 全量测试 + compileall → 构建真实 EXE → 走查 → 更新 `UI_FINAL_AUDIT.md`。
4. 重新签署本冻结声明（更新版本 / SHA / 时间）。

---

## 5. 发布前提醒
- **代码签名**：当前未签名，建议在带证书环境执行 `signtool sign`（见 `build.bat` 注释块）后再发布。
- **目检**：建议在带显示环境打开 `dist/DesktopCleaner.exe` 做最终像素级目检（本冻结审计已在无显示环境用 headless 构造校验替代）。
