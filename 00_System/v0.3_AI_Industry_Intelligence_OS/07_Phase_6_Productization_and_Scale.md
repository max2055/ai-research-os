# Phase 6：Dashboard、持续运行、规模化与 v0.3 发布

状态：`proposed`  
建议周期：5–8 周 + 30 天真实 Pilot  
前置：Phase 2–5 工程 Gate  

## 1. 阶段目标

把分散能力组装成可每日使用、可监控、可恢复的本地研究产品：

- Industry Home 和 Daily Brief；
- Sector、Company、Technology、Paper、Impact、Analysis、Forecast、Decision 页面；
- scheduler、Candidate DB、Markdown 和 Source assets 的统一健康检查；
- 性能、备份、恢复、迁移、数据许可和成本治理；
- 30 天真实研究 Pilot；
- v0.3 人工发布决定。

## 2. 目标信息架构

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

Dashboard 默认继续 loopback-only。Web mutation 是否引入必须另行批准；v0.3 可以先用
CLI/Markdown 完成所有权威写入。

## 3. 页面要求

### Industry Home

- 今日高优先级 Candidate；
- reviewed Event/Impact 更新；
- 反面与冲突信号；
- stale Core Company/Channel；
- due Forecast/Action；
- Sector heatmap（明确指标，不做黑箱情绪分）；
- 数据新鲜度和运行失败。

### Sector

- 定义、范围、价值链位置；
- 上游/下游；
- Core/Tracked Company；
- Technology/Product；
- supply/demand/price/capacity metrics；
- Event timeline；
- reviewed Impact paths；
- active Thesis/Forecast；
- coverage completeness。

### Company

- Company 与 Security 分离展示；
- 产品、技术和板块；
- supplier/customer/competitor assertions；
- Source Channel freshness；
- operating metrics；
- Evidence timeline；
- Analysis Runs；
- Forecast、Valuation 和 Recommendation history。

### Candidate Queue

- status、Channel、Sector、Entity、评分分项、duplicate cluster；
- 原始 locator；
- promote/dismiss 建议；
- reviewed Evidence 与 Candidate 明显分区。

### Decision Desk

- open Forecast；
- due/overdue resolution；
- Scenario；
- Valuation freshness；
- active Recommendation；
- catalysts/falsifiers；
- calibration，不用短期 leaderboard 误导。

## 4. 存储与规模决策

### 保持当前分层

- Markdown：权威研究对象；
- assets：原始证据；
- SQLite Candidate DB：operational；
- SQLite derived ontology/search：可重建；
- Git：代码和 Markdown 版本；
- 加密离机备份：assets + operational snapshots。

### 评估 PostgreSQL 的触发条件

满足一个持续性条件再评估：

- Candidate >100k 且 SQLite 写锁/查询影响日常运行；
- 多进程 scheduler 并发写成为真实瓶颈；
- 两名以上用户需要稳定远程查询；
- 增量 materialized view 无法由 SQLite 可靠维护；
- 30 天性能记录显示 p95 超出 Gate。

### 评估图数据库的触发条件

- 关系类型稳定至少两个复盘周期；
- reviewed edges >50k；
- 每周高频三跳以上解释查询；
- SQL recursive CTE/in-memory graph 有测量瓶颈；
- 能定义单向同步、备份、重建和回写禁止策略。

### 评估向量索引

仅用于：Candidate/Source 语义检索、近似重复、相关段落召回。不得用于来源权威、事实确认、
Evidence independence 或自动 Thesis 更新。

## 5. SLO 与性能预算

本地单用户建议目标：

| 操作 | 目标 |
|---|---:|
| Dashboard Home p95 | <2 秒 |
| Candidate Queue p95 | <2 秒/10k filtered records |
| Company/Sector page p95 | <2 秒 |
| 3-hop Impact query p95 | <3 秒/50k edges |
| Daily discovery batch | <30 分钟/Pilot Channels |
| Source promote transaction | <10 秒，不含大文件网络下载 |
| full validate | <30 秒/5k formal objects |
| index rebuild | <30 秒/5k formal objects |
| recovery | RTO <4 小时，RPO ≤24 小时 operational data |

超过目标必须先 profile，再决定数据库或缓存，不凭感觉迁移。

## 6. 运行与可观测性

Health 必须覆盖：

- Channel enabled/review/license state；
- last success、next due、missed run；
- Candidate DB migration/version/integrity；
- dead-letter、retry exhaustion；
- Source asset MISSING/HASH_MISMATCH；
- repository validation/index drift；
- stale Entity/Metric/Valuation；
- failed Analysis/Forecast jobs；
- disk space、backup age、clock/timezone；
- secret/config presence，只显示状态不显示值；
- model/API cost budget。

告警分级：

- P0：资产 hash mismatch、数据库损坏、secret 泄露、事务不一致；
- P1：连续漏跑、备份过期、关键 Channel 失败、reviewed 引用损坏；
- P2：单 Channel 失败、stale coverage、评分漂移；
- P3：一般噪声和优化建议。

## 7. 备份与恢复

必须分别恢复：

1. Git 中的代码和 Markdown；
2. Source assets 加密归档；
3. Candidate DB snapshot；
4. secrets/config（不进 Git）；
5. launchd 配置；
6. 可重建 indexes/ontology/search。

恢复演练：

- clean directory clone；
- 安装 package；
- 恢复 assets；
- 恢复 Candidate snapshot；
- 验证 DB integrity/migration；
- 重建 indexes/ontology；
- validate/hash/tests；
- 启动 Dashboard；
- replay 一个 discovery run；
- 验证 Candidate↔Source links；
- 记录 RTO/RPO 和未恢复项。

## 8. 安全与许可 Gate

- secrets 不进 Git/Markdown/log；
- Dashboard loopback；
- HTML escape、path traversal、asset ownership tests；
- 外部内容视为不可信输入；
- 下载大小、media type、redirect、timeout 限制；
- license/robots 复查日期；
- 付费数据展示和派生符合合同；
- 模型 provider 的数据保留策略记录；
- prompt injection 内容不能改变系统规则或执行命令；
- 日志可审计但不含正文/凭证等敏感数据。

## 9. 工作包

| ID | 任务 | 交付 | 验收 |
|---|---|---|---|
| F-001 | Product IA/spec | Dashboard design v2 | 页面/查询/边界批准 |
| F-002 | read model v2 | service/API | Candidate+Universe+Evidence 组合 |
| F-003 | Industry Home | UI | daily priority/freshness/health |
| F-004 | Sector pages | UI | value chain/entities/metrics/impact |
| F-005 | Company Radar | UI | entity/security/evidence/decision |
| F-006 | Candidate Queue | UI | filters/score/cluster/status |
| F-007 | Impact Explorer | UI | graph+table+mechanism/conflicts |
| F-008 | Analysis Workspace | UI | run input/version/compare |
| F-009 | Decision Desk | UI | forecast/valuation/recommendation |
| F-010 | unified operations | UI/services | schedule/jobs/actions/due |
| F-011 | unified health | UI/services | repo/assets/DB/channels/backup |
| F-012 | caching/profile | benchmark | cache 可删除，no stale authority |
| F-013 | SLO benchmark | benchmark docs | Pilot 和 scale 数据 |
| F-014 | security tests | tests/audit | injection/path/secret/input limits |
| F-015 | license audit | review packet | 每个 enabled Channel 合规状态 |
| F-016 | backup automation | runbook/jobs | daily snapshot + age alert |
| F-017 | full recovery drill | recovery record | RTO/RPO 与完整性 Gate |
| F-018 | migration rehearsal | clean copy | v0.2→v0.3 可回滚 |
| F-019 | user runbook | docs | install/daily/weekly/monthly/failure |
| F-020 | Known Limitations v0.3 | system doc | 数据、模型、许可、决策边界 |
| F-021 | 30-day Pilot | real operation | daily/weekly/monthly records |
| F-022 | Forecast resolution Gate | real resolutions | 不预填未来结果 |
| F-023 | release check v0.3 | service/tests | machine-verifiable checklist |
| F-024 | human release packet | review doc | reviewer/date/decision |
| F-025 | final tag/release | release engineering | 仅在全 Gate 后 |

## 10. 30 天 Pilot

范围固定：

- 8–10 Pilot Sector；
- 30–50 Core Company；
- 20–40 enabled Channel；
- 每日 Candidate triage；
- 每周 Evidence/Impact/Forecast review；
- 一次 Monthly coverage/calibration review；
- 3 家公司 Decision Pilot；
- 不在 Pilot 中途无审批扩大 Universe。

记录：

- 每日候选、Top-N precision、人工耗时；
- promote/dismiss/duplicate/failure；
- Source→Event latency；
- Impact edit/retention；
- Mode usefulness和遗漏；
- Forecast open/resolved/ambiguous；
- stale coverage；
- scheduler/backup/health；
- 用户认为节省或增加的工作量；
- 所有产品代码修改和原因。

## 11. v0.3 Release Gate

### Evidence/Universe

- [ ] Pilot Universe 达标且抽检通过。
- [ ] 所有 authoritative 对象引用可解析。
- [ ] 0 validation error；0 unexplained warning。

### Ingestion

- [ ] 14 天 Candidate Gate 和 30 天 Pilot 完成。
- [ ] 无静默漏跑、无越权抓取。
- [ ] enabled Channel license 全部 reviewed。

### Impact/Analysis

- [ ] 20-event Impact Field Gate 通过。
- [ ] 10-case Mode Field Gate 通过。
- [ ] 反面路径和不同模式分歧可见。

### Decision

- [ ] 10 个人工批准 Forecast。
- [ ] 至少一批自然到期并真实 Resolution。
- [ ] 3 家公司 Recommendation Draft Pilot。
- [ ] 无自动 buy/sell/position/execution。

### Engineering

- [ ] tests/coverage/ruff/mypy 全绿。
- [ ] 性能 SLO 通过或限制明确。
- [ ] migration/rollback/recovery 通过。
- [ ] Candidate DB、assets、Git、secrets 恢复边界明确。
- [ ] Dashboard smoke 和安全检查通过。

### Human

- [ ] 两次 Weekly 和一次 Monthly v0.3 review。
- [ ] Known Limitations 已读。
- [ ] Release packet 有命名 reviewer、日期和 approve 决定。

## 12. 发布后

- 每月 review Channel quality、Universe coverage、Forecast calibration 和模式表现；
- 每季度 review Taxonomy/Ontology 关系；
- 新 Sector 批次化加入，每批通过 coverage Gate；
- 新数据源先 license review；
- 新分析模式先 sandbox 和 field gate；
- PostgreSQL、图数据库、向量索引只按实际瓶颈触发；
- Recommendation 若扩展到 buy/sell/position，另起 v0.4 治理项目。

