# Dashboard Design v2（Product IA）

版本：v2.0（WP-600 F-001）  
生效日期：2026-08-09  
基线批准：RCP-v03-010（2026-08-09，max）  
前置：`00_System/Dashboard_and_Jobs_Design.md`（v1.0，RCP-20260729-006）

## 1. 目标信息架构（IA v2）

来自 `07_Phase_6_Productization_and_Scale.md` §2，作为 Phase 6 页面/查询/边界基线：

```text
Industry Home
├── Daily Brief
├── Sector Map
│   ├── Sector detail
│   ├── Core/Tracked companies
│   ├── technologies/products
│   ├── key metrics
│   └── latest events/impacts
├── Company Radar
│   ├── profile/security
│   ├── supply/customer/competition
│   ├── events/theses/forecasts
│   └── valuation/recommendations
├── Candidate Queue
├── Evidence Review Queue
├── Impact Explorer
├── Analysis Workspace
├── Forecast & Decision Desk
├── Operations
└── System Health
```

## 2. 页面 → 查询/边界表

| 页面 | route | read-model fn | data boundary | write boundary | §3 ref |
|---|---|---|---|---|---|
| 产业首页（Industry Home）| `/home` | `industry_home_snapshot`（F-002）| 候选+Universe+Evidence+Decision 聚合 | none（GET-only）| §3 Industry Home |
| 概览（Project overview）| `/` | `_project_overview`（app.py）| 单 Project 作用域 | none | — |
| Daily Brief | CLI/job Markdown 产物（web 入口随 WP-601）| `daily_brief` | 候选+通道+事件+失败 | none | §3 Industry Home |
| Sector Map | `/sectors`（现有）| (WP-601/602) | 板块/公司/事件/影响 | none | §3 Sector |
| Company Radar | `/companies`（现有）| (WP-601/602) | 实体/安全/证据/决策 | none | §3 Company |
| Candidate Queue | `/pipeline/queue`（现有）| `queue_rows` | 候选 SQLite operational store | none | §3 Candidate Queue |
| Evidence Review Queue | `/reviews`（现有）| `render_review_queue` | reviewed/pending 对象 | none | — |
| Impact Explorer | `/impact`（现有）| `render_impact` | 影响断言/路径 | none | — |
| Analysis Workspace | `/analysis`（现有）| `analysis_*` services | mode/run 对象 | none | — |
| Forecast & Decision Desk | `/decision`（现有）| `forecast_status_report` 等 | forecast/valuation/rec | none | §3 Decision Desk |
| Operations | `/operations`（现有）| `action_rows` 等 | action/review due | none | — |
| System Health | `/health`（现有）| `verify_source_assets` 等 | validation/index/asset/job | none | — |
| 模型配置 | `/llm`（现有）| `llm_config` | 本地 config store | `/llm/config` `/llm/models` `/llm/test`（grandfather）| — |

## 3. Read model 约定

- HTTP request 直接运行 repository validation 与查询；页面只读 canonical Markdown、本地 Source assets 与 Candidate SQLite operational store。
- 两层结构：**query fn**（`*_rows`/`*_metrics`/`*_report`/`*_status`，返回 dict/list）+ **render fn**（`render_*` 返回 HTML/Markdown）。query fn 永不写入。
- 组合模型：`daily_brief`（`services/brief.py`）是跨域组合先例；F-002 `industry_home_snapshot` 是其 dashboard 侧实例，聚合 candidate + Universe + Evidence + Decision。
- UI 不持久化对象副本；删除任何浏览器或临时 cache 后下一请求自然重建。快照永远不是权威。
- `/api/state` 是派生 JSON read model，不是写入 API。
- `Home_Dashboard.md` 是 Obsidian fallback，由 index service 重建。

## 4. GET-only 不变量

- 除 3 个 grandfather `/llm` POST（`/llm/config`、`/llm/models`、`/llm/test`，供应商本地配置，Key 不离开服务端）外，所有 route 必须 GET-only。
- WP-600/601/602 禁止新增 POST/PUT/PATCH/DELETE；权威写入一律走 CLI + Markdown + dry-run/`--apply`（RCP-v03-010）。
- 回归网：`test_m5_dashboard_jobs.py` 动态重算非 GET 路径集，断言恰好等于上述 3 个。

## 5. Loopback + no-mutation

- `research-os ui` 默认 `127.0.0.1:8765`；只接受 loopback host（`run_ui` 拒绝非 loopback）。
- 无 web mutation route；浏览器不写任何权威研究对象。
- 仓库文本在 HTML 输出前 escape；Source asset 通过拥有它的 Source 与数组 index 解析，拒绝任意 path。
- 不处理登录、账户或公网访问。

## 6. WP-600 范围

- 本 WP 仅 F-001/F-002/F-003：IA spec、`industry_home_snapshot` read model、`/home` Industry Home UI。
- F-004+（Sector/Company/Candidate/Impact/Analysis/Decision 页面重排）延后 WP-601/602；其上表路由/查询受本 IA 约束。
- `/` 路由决策（2026-08-09 max）：保留 `/` 为 Project overview；Industry Home 落在新 `/home`。nav 本次仅加「产业首页」入口，完整重排随 WP-601/602。
- v0.3 发布（F-021~025）仍被 WP-530 自然到期阻塞（最早 2026-10-31），工程可先行。
