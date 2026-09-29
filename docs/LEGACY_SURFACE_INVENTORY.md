# 遗留 / 保留产品表面清单（LEGACY / RESERVED PRODUCT SURFACE）

| 项 | 值 |
|---|---|
| 记录日期 | 2026-09-29（PHASE 0 Baseline Closure） |
| 状态 | **NOT ACTIVE — 运行期不可达（unreachable）** |
| 处置原则 | **保留，不删除。** 视为产品历史资产与预留表面，禁止以"代码更干净"为由清理。 |

---

## 一、为什么记录这份清单

PHASE 0 基线审计发现：若干模块仍被构造 / 互相引用，但**从运行期 UI 无法到达**。
它们不是缺陷，而是产品演进（UI-1.3 导航收口、Decision 02）留下的**预留表面**。
按实施纪律：**不删除**，仅登记其不可达状态，避免后续误判为"死代码"而误删。

**判定依据**（offscreen 实测，非静态推断）：

```
AppShell._pages   = ['custom', 'history', 'home', 'large', 'organize', 'settings']
Sidebar 可达入口  = ['about', 'history', 'large', 'organize', 'settings']
```

凡在 `_pages` 中但不在 Sidebar 入口内的页面，运行期即不可达。

---

## 二、不可达表面清单

| 模块 | 行数 | 不可达原因 | 处置 |
|---|---|---|---|
| `src/ui/pages/tools_page.py` | 124 | "更多工具"已从导航移除（UI-1.3 Decision 02）；`AppShell._pages` 中亦无 `tools` 键 | 保留 |
| `src/ui/coming_soon.py` | 74 | 仅被 `tools_page` 引用，而 `tools_page` 自身不可达 | 保留 |
| `src/ui/features.py` | 166 | 仅被 `tools_page` / `coming_soon` 引用（**功能注册中心**，含 10 项路线图） | 保留（路线图唯一事实来源） |
| `src/ui/pages/dashboard_page.py` | 240 | Sidebar 无 `home` 入口（UI-1.3 Phase 1.5 起"整理"即产品首页） | 保留 |
| `src/ui/pages/custom_page.py` | 192 | Sidebar 无 `custom` 入口（P1-5 起从导航移除，但仍在 `_pages` 实例化） | 保留 |

合计约 **796 行**保留表面。**本轮（PHASE 0 / V1.2-A）不触碰、不删除、不重构。**

---

## 三、注意事项

1. **`ui/features.py` 不是死代码，是路线图。** V1.2-A 要落地的 `EMPTY_FOLDER` / `FOLDER_ANALYZER`
   等条目就定义在此。新增功能时按既有约定翻转 `status`，UI 会自动反映。
2. **`dashboard_page` / `custom_page` 仍在 `AppShell._pages` 中被实例化**，因此它们的
   `__init__` 会真实执行——对它们做修改仍需回归测试（本轮对 `dashboard_page` 的
   Worker 生命周期修复即属此类）。
3. 若未来决定正式弃用某个表面，应**单独开阶段**处理（删除 + 同步 `build.spec`
   `hiddenimports` + 更新本清单 + 更新 README §八），不得顺手删除。
