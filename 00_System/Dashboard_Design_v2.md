# Dashboard Design v2（Product IA）

版本：v2.1（Web-only migration contract）

生效日期：2026-08-12

基线批准：RCP-v03-010（IA）+ RCP-v03-011（Web mutation / CLI retirement）
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

| 页面 | route | read-model fn | data boundary | target write boundary | §3 ref |
|---|---|---|---|---|---|
| 产业首页（Industry Home）| `/home` | `industry_home_snapshot`（F-002）| 候选+Universe+Evidence+Decision 聚合 | 导航到具名 workflow，不在聚合快照内直接写 | §3 Industry Home |
| 概览（Project overview）| `/` | `_project_overview`（app.py）| 单 Project 作用域 | none | — |
| Daily Brief | Web + scheduled Markdown 产物 | `daily_brief` | 候选+通道+事件+失败 | 手动运行/审阅，自动任务无审批权 | §3 Industry Home |
| Sector Map | `/sectors`（现有）| (WP-601/602) | 板块/公司/事件/影响 | none | §3 Sector |
| Company Radar | `/companies`（现有）| (WP-601/602) | 实体/安全/证据/决策 | none | §3 Company |
| Candidate Queue | `/pipeline/queue`（现有）| `queue_rows` | 候选 SQLite operational store | dismiss/restore/promote：各自 `/{candidate_id}/{operation}/preview` → `/{operation}/commit` | §3 Candidate Queue |
| Evidence Review Queue | `/reviews`（现有）| `render_review_queue` | reviewed/pending 对象 | none | — |
| Impact Explorer | `/impact`（现有）| `render_impact` | 影响断言/路径 | none | — |
| Analysis Workspace | `/analysis`（现有）| `analysis_*` services | mode/run 对象 | none | — |
| Forecast & Decision Desk | `/decision`（现有）| `forecast_status_report` 等 | forecast/valuation/rec | none | §3 Decision Desk |
| Operations | `/operations`（现有）| `action_rows` 等 | action/review due | none | — |
| System Health | `/health`（现有）| `verify_source_assets` 等 | validation/index/asset/job | none | — |
| 模型配置 | `/llm`（现有）| `llm_config` | 本地 config store | `/llm/config` `/llm/models` `/llm/test`（grandfather）| — |

## 3. Read model 约定

- 查询型 HTTP request 直接运行 repository validation 与 query function；页面读取 canonical Markdown、本地 Source assets 与 Candidate SQLite operational store。mutation route 必须经过 §4 的独立写入合同。
- 两层结构：**query fn**（`*_rows`/`*_metrics`/`*_report`/`*_status`，返回 dict/list）+ **render fn**（`render_*` 返回 HTML/Markdown）。query fn 永不写入。
- 组合模型：`daily_brief`（`services/brief.py`）是跨域组合先例；F-002 `industry_home_snapshot` 是其 dashboard 侧实例，聚合 candidate + Universe + Evidence + Decision。
- UI 不持久化对象副本；删除任何浏览器或临时 cache 后下一请求自然重建。快照永远不是权威。
- `/api/state` 是派生 JSON read model，不是写入 API。
- `Home_Dashboard.md` 是 Obsidian fallback，由 index service 重建。

## 4. Web mutation 不变量

- 当前 exact non-GET allowlist 为 9 条 POST：3 条 `/llm/*` 本地配置路由，加 Candidate
  dismiss、restore、promote 各自的 preview 与 commit。新增 route 必须显式更新
  capability/security contract。
- 新 mutation route 必须调用既有领域 service，先返回 validation + diff preview，再由具名人工
  对明确 target version 提交；不得直接编辑浏览器副本或绕开 Markdown authority。
- 每次提交记录 actor、decision、timestamp、target ID、before/after version、结果与失败原因，
  并具备防重复、并发冲突检测、原子失败和可验证回滚。
- 自动任务、Agent 和模型输出只能产生 pending 草稿或 operational 更新，不能调用审批动作，
  不能改变 Thesis 结论或 confidence。
- 路由回归测试固定当前 9 条 POST allowlist，并逐 route 校验 capability、CSRF/Origin、权限、
  audit 和 transaction contract。

## 5. Loopback + controlled mutation

- `research-os ui` 默认 `127.0.0.1:8765`；只接受 loopback host（`run_ui` 拒绝非 loopback）。
- F-026/F-027A 已实现 Candidate dismiss、restore 和 promote：固定本地具名 identity、
  session-bound CSRF、10 分钟签名 preview token、单次 nonce、target-version 并发检查；
  restore 的 Candidate/action/audit 在一个 SQLite transaction 内提交，promote 对 preview
  冻结的 Source/assets、Candidate action 与 audit 做协调提交并留存失败补偿 manifest。
  Candidate 是 operational state；promote 只创建 pending Source，不自动批准；Review、
  Thesis 与其他权威研究对象区域仍保持 GET-only。
- 仓库文本在 HTML 输出前 escape；Source asset 通过拥有它的 Source 与数组 index 解析，拒绝任意 path。
- 当前不处理登录、账户或公网访问；远程/多用户能力必须另建身份认证、授权与部署 RCP。

## 6. WP-600 范围

- 本 WP 仅 F-001/F-002/F-003：IA spec、`industry_home_snapshot` read model、`/home` Industry Home UI。
- F-004+（Sector/Company/Candidate/Impact/Analysis/Decision 页面重排）延后 WP-601/602；其上表路由/查询受本 IA 约束。
- `/` 路由决策（2026-08-09 max）：保留 `/` 为 Project overview；Industry Home 落在新 `/home`。nav 本次仅加「产业首页」入口，完整重排随 WP-601/602。
- v0.3 发布（F-021~025）仍被 WP-530 自然到期阻塞（最早 2026-10-31），工程可先行。

## 7. Web-only migration scope

- F-026：已完成 Candidate dismiss 与共享 mutation preview/commit、具名 actor、审计、
  optimistic concurrency、schema v3 rollback 基础。
- F-027：Candidate、Evidence、Impact、Analysis、Forecast、Decision、Review 与 Thesis
  proposal 人工流程 Web parity 已完成。
- F-028：Channel、website-hosted scheduler、health、backup、restore、validation、index 和
  release parity 已完成；Worker 只在网站 lifespan 内运行。
- F-029：用户文档无产品 CLI；包级 CLI entry point 与内部 `ui` 叶已删除。生产入口从
  imported package 解析 canonical root，启动前执行 Runtime Identity preflight。
