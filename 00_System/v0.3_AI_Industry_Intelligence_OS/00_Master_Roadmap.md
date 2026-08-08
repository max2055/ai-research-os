# AI Industry Intelligence & Decision OS v0.3 总路线图

状态：`proposed / pending human approval`  
版本：v0.3-plan-1  
制定日期：2026-08-04  
继承基线：AI Research OS v0.2 Evidence Kernel  
目标用户：本地单用户 AI 产业与投资研究者  

> 本目录是实施规划，不是已经生效的 Research Rule、Taxonomy 或 Schema。
> 任何改变现有规则、对象 Schema、永久 ID、审核边界或事实源的实施，都必须先建立
> Rule Change Proposal 并由研究者批准。

## 1. 目标定义

v0.3 的目标不是继续扩充企业软件专题，而是在 v0.2 证据治理内核之上建设：

> 覆盖 AI 全产业链、持续发现高价值资讯与论文、以 Ontology 组织企业和技术关系、
> 解释事件跨板块传导、支持多种分析模式、记录可校准预测，并形成需人工批准的
> 投资研究建议草稿。

目标闭环：

```text
AI Industry Universe
→ Source Channel Registry
→ Scheduled Candidate Discovery
→ Dedup / Relevance / Novelty / Entity Resolution
→ Canonical Source Capture
→ Anchored Event & Evidence
→ Time-aware Industry Ontology
→ Causal Impact Assertions and Paths
→ Versioned Analysis Modes
→ Forecast / Scenario / Valuation
→ Recommendation Draft
→ Human Review
→ Outcome Resolution and Calibration
```

## 2. v0.2 基线与继承原则

规划制定时的真实基线：

- 166 个正式对象；
- 39 Source、31 Event、8 Thesis、8 Company、2 Report；
- 0 validation error、0 warning；
- 98 tests，84.03% coverage；
- Source 原始资产、SHA-256、版本、citation anchor 和 Review Decision 已实现；
- Dashboard、Job Run、Project scope、Metrics、JSONL/SQLite Ontology 导出已实现；
- v0.2 真实 Weekly/Monthly cadence 与最终发布决定仍待完成。

必须继承：

1. Fact、Inference、Judgment 分离。
2. 关键事实必须有可追溯 Source。
3. AI 产物默认 pending。
4. Source processing 不等于 Source review。
5. 支持和反面 Evidence 同时保留。
6. Thesis confidence 不得自动改变。
7. 自动化不得生成权威买卖指令。
8. 原始 Source asset 不覆盖。
9. 写操作 dry-run 优先，显式 `--apply`。
10. 每个新能力必须可验证、可回滚、可交接。

## 3. 产品分层

| 层 | 职责 | 建议事实源 |
|---|---|---|
| Universe | 板块、公司、证券、产品、技术、指标和来源配置 | reviewed Markdown entities/config |
| Candidate Intelligence | 高频候选、抓取状态、评分和去重簇 | 可重建 SQLite operational store |
| Evidence Kernel | Source、Event、Thesis、Report、Review | 现有 canonical Markdown + assets |
| Ontology | 稳定实体关系与带证据的时间关系 | reviewed Markdown assertions；SQL/graph 为派生视图 |
| Impact | 事件到板块、公司和财务变量的因果传导 | pending/reviewed Impact Assertion |
| Analysis | 可版本化的分析模式与运行结果 | mode definition + immutable run artifact |
| Decision | Forecast、Scenario、Valuation、Recommendation Draft | reviewed Markdown objects |
| Evaluation | Forecast resolution、calibration、模式表现 | append-only resolution records |
| Experience | Daily Brief、产业地图、公司雷达、影响图、决策台 | 可重建 Dashboard read model |

Candidate 数据量预计远大于正式研究对象，因此不能把每条候选新闻都写成正式 Source。
正式研究结论仍以 Markdown 对象和人工审核为权威边界。

## 4. 阶段总览

| 阶段 | 名称 | 建议周期 | 核心 Gate | 依赖 | 状态 |
|---|---|---:|---|---|---|
| 0 | 产品重定义与治理准备 | 1–2 周 | Charter、RCP、边界获批 | v0.2 基线 | ✅ 完成（2026-08-05）|
| 1 | AI Taxonomy、Ontology 与 Universe | 3–5 周 | 8–10 板块、30–50 Core Company、关系可验证 | 阶段 0 | ✅ 完成（2026-08-06）|
| 2 | 每日情报发现与 Candidate Pipeline | 5–7 周 | 连续稳定运行、无静默丢失、可控噪声（触发条件见 B-026 §触发条件，非固定日期，见 D-CALENDAR-DECOUPLE）| 阶段 1 | ⬜ in_progress |
| 3 | Impact Assertion 与跨板块传导 | 4–6 周 | 20 个真实事件的人工影响路径 Gate | 阶段 1–2 | ✅ 完成（2026-08-08，C-018 approved + 多跳激活）|
| 4 | Analysis Mode Framework | 4–6 周 | 6 个模式、同证据可复现、差异可解释 | 阶段 3 | ⬜ in_progress |
| 5 | Forecast、Valuation 与 Recommendation Draft | 5–7 周 | 可解析预测、三情景、人工建议 Gate | 阶段 4 | ⬜ proposed |
| 6 | Dashboard、规模化、运行与发布 | 5–8 周 | 30 天 pilot、恢复、性能、治理和发布 Gate | 阶段 2–5 | ⬜ proposed |

单 Agent 串行估算约 27–41 周。多个 Agent 可以并行处理 Adapter、UI、Schema 测试和
Universe 数据，但 Schema、Taxonomy、同一对象和最终报告不得无人协调并行修改。

## 5. 文档索引与执行顺序

1. `01_Product_Charter_and_Governance.md`
2. `02_Phase_0_1_Ontology_and_Universe.md`
3. `03_Phase_2_Intelligence_Ingestion.md`
4. `04_Phase_3_Impact_Engine.md`
5. `05_Phase_4_Analysis_Mode_Framework.md`
6. `06_Phase_5_Forecast_and_Investment_Decision.md`
7. `07_Phase_6_Productization_and_Scale.md`
8. `08_Agent_Execution_Protocol.md`
9. `09_Master_Backlog.md`

Agent 开工前必须同时读取根目录 `AGENTS.md` 和本目录相关阶段文件。

## 6. 全局 Definition of Done

任何阶段只有同时满足以下条件才可标记 completed：

- 阶段范围和非目标没有静默变化；
- 所需 RCP 已获人工批准；
- Schema、CLI、API、UI 和文档与实现一致；
- 新对象/关系有 validation；
- happy path、失败、幂等、事务回滚和兼容测试齐全；
- 全仓库 `validate` 为 0 error；
- global、PRJ-001、PRJ-002 及新增 Pilot project index drift 为 0；
- tests、coverage、ruff、mypy 通过；
- 真实资料 Gate 由研究者完成，不用 fixture 替代；
- Source/Thesis/Recommendation 没有被自动权威化；
- migration、rollback、backup 和 recovery 已演练；
- Known Limitations、运行手册、交接记录已更新；
- 工作区只包含本工作包范围内的可解释修改。

## 7. 全局非目标

v0.3 不应默认包含：

- 自动交易、券商下单或无人值守仓位调整；
- 以多 Agent 投票替代证据判断；
- 无边界抓取全网；
- 绕过登录、付费墙、robots 或访问控制；
- 把所有 Candidate 永久保存为正式 Source；
- 用相关性边自动宣称因果关系；
- 让模型自动修改 Source grade、Thesis confidence 或 Recommendation status；
- 把向量相似度作为事实或来源独立性证明；
- 在没有价格、时间、市场和估值来源时生成证券建议；
- 在关系类型未稳定前引入不可回写的图数据库事实源；
- 为追求覆盖率而牺牲来源许可、可追溯性或人审边界。

## 8. 建议 Pilot

第一个 v0.3 Pilot 选择“AI Compute Infrastructure Chain”：

```text
半导体材料与设备
→ 晶圆制造、先进封装与测试
→ GPU / ASIC / CPU
→ HBM / DRAM / Storage
→ Server / Network / Optics
→ Datacenter / Power / Cooling
→ Cloud AI Infrastructure
→ Foundation Model Demand
```

选择理由：

- 能验证多板块、多公司和多跳关系；
- 原始来源相对丰富；
- 供给、成本、产能和资本开支机制可观察；
- 能暴露“技术需求增长”和“公司股东回报”之间的中间环节；
- 比先覆盖全部应用更容易定义稳定 Ontology。

第二个 Pilot 再覆盖“模型—Agent 平台—企业应用”，验证需求侧和软件价值迁移。

## 9. 关键人工决策点

| 决策 | 最晚时间 | 自动化能否代替 |
|---|---|---|
| 是否接受 v0.3 产品重定义 | 阶段 0 前 | 否 |
| Taxonomy v2 一级/二级分类 | 阶段 1 写入前 | 否 |
| 新正式对象类型和永久 ID | Schema migration 前 | 否 |
| Candidate operational store 的事实边界 | 阶段 2 前 | 否 |
| Impact 关系类型与强度语义 | 阶段 3 前 | 否 |
| Analysis Mode 权威边界 | 阶段 4 前 | 否 |
| Forecast 和 Recommendation 等级 | 阶段 5 前 | 否 |
| 是否扩大 Universe | 每个 Pilot Gate 后 | 否 |
| 是否采用 PostgreSQL/图数据库 | 触发量化瓶颈后 | 否 |
| v0.3 发布决定 | 30 天 Pilot 后 | 否 |

## 10. 成功标准

v0.3 成功不是“抓到很多新闻”，而是：

1. 每日候选稳定到达且重复、噪声和失败可测量。
2. 高价值候选能在可接受时间内被提升为可追溯 Source/Event。
3. 任一重要影响路径可解释每一跳的机制和 Evidence。
4. 多分析模式的结论差异能定位到假设、时间范围或证据权重。
5. Forecast 能在到期后解析并进入校准统计。
6. Recommendation Draft 同时包含估值、反证、风险和失效条件。
7. 系统能从 Git、资产备份和 operational store snapshot 恢复。
8. 研究者能在每日 30–60 分钟内完成核心情报审阅，而不是被候选淹没。

