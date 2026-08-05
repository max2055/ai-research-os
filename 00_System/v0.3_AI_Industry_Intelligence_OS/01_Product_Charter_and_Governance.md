# v0.3 产品章程与治理边界

状态：`proposed / pending human approval`  
依赖：`00_Master_Roadmap.md`  

## 1. 产品定位

产品名称：AI Industry Intelligence & Decision OS。  
底层产品：AI Research OS Evidence Kernel v0.2。

核心工作：

- 维护 AI 产业 Universe；
- 持续发现可信资讯、论文和经营信号；
- 将高价值变化提取为可追溯 Evidence；
- 用 Ontology 表达企业、产品、技术和价值链关系；
- 生成可解释的直接和间接影响路径；
- 通过不同分析模式形成竞争性解释；
- 记录可证伪 Forecast、Scenario 和投资研究建议草稿；
- 通过结果解析和校准改进研究过程。

## 2. 用户与主要任务

首要用户：单一 AI 产业与投资研究者。  
次要执行者：编码 Agent、研究 Agent、采集任务和本地 scheduler。

主要任务：

1. 查看今日 AI 产业最重要的 10–30 条候选，而不是全部资讯。
2. 进入某板块查看关键公司、技术路线、供需变量和最新变化。
3. 进入某公司查看产品、证券、上下游、竞争、经营指标和 Thesis。
4. 从 Event 查看一至三跳影响，以及每一跳的机制和 Evidence。
5. 用多种 Analysis Mode 重新分析同一 Evidence set。
6. 比较模式间的共同结论、分歧、假设和 unknowns。
7. 建立有明确期限、概率和解析条件的 Forecast。
8. 将产业判断与价格、市场预期和估值结合为 Recommendation Draft。
9. 在预测到期后记录结果并查看模式和研究者的历史校准。

## 3. 权威性分层

| 数据/产物 | 默认状态 | 能否直接用于权威结论 | 审核要求 |
|---|---|---|---|
| Candidate | discovered | 否 | 可自动分类；提升前人工/规则确认 |
| Source | pending | 否 | Source-level human review |
| Event | pending | 否 | Fact anchor + Event-level human review |
| Stable entity | pending update | 否 | reviewed Evidence + human merge |
| Ontology edge proposal | pending | 否 | 关系语义和 Evidence review |
| Impact Assertion | pending | 否 | mechanism、direction、horizon review |
| Analysis Run | draft | 否 | 只代表某模式输出 |
| Thesis | pending/reviewed | 仅 reviewed 可权威引用 | 人工决定方向和 confidence |
| Forecast | open/pending | 否 | 人工批准后成为正式预测 |
| Valuation Snapshot | pending | 否 | 日期、价格、口径和来源审核 |
| Recommendation Draft | pending | 否 | 人工批准且不得自动执行 |
| Resolution | pending | 否 | 结果来源与判定人工确认 |

## 4. Candidate 与 Source 的边界

Candidate 是低成本、高吞吐的发现记录，允许：

- 标题、摘要、URL、发布日期候选；
- 来源 Channel；
- hash、canonical URL、duplicate cluster；
- entity/sector proposal；
- relevance、novelty、quality proposal；
- discovery time、fetch status 和错误；
- retention policy。

Candidate 不允许：

- 被 Report 当作事实引用；
- 自动提升 Source grade；
- 自动支持或反对 Thesis；
- 自动生成 Recommendation；
- 在没有捕获正文时伪装成已归档 Source。

正式 Source 必须继续满足 `Source_Policy.md` 和 Source Asset Store 要求。

## 5. 建议数据事实源

### 5.1 Canonical Markdown

保存：

- reviewed/pending 正式研究对象；
- Universe 和稳定实体；
- 需审计的关系/影响/模式/预测/建议；
- Review Decision、Action、Report；
- 配置中需要 Git review 的稳定部分。

### 5.2 Source Asset Store

保存原始 HTML、PDF、文本、manifest、提取物和 hash。原始 bytes 不覆盖。

### 5.3 Candidate Operational Store

建议初期使用 SQLite，保存高频、可重建的候选和调度状态。它不是研究事实源。

必须提供：

- Schema version；
- deterministic migration；
- export/import；
- backup/snapshot；
- retention；
- 从 Channel 配置重新发现的边界说明；
- Candidate 提升为 Source 后的永久关联。

### 5.4 Derived Ontology/Search Store

SQLite/PostgreSQL/graph/vector index 均为派生查询层，不接受绕过 Markdown 审核的
权威写入。

## 6. 研究与投资边界

系统可以输出：

- Watch；
- Research priority；
- Thesis；
- Investment candidate；
- Recommendation Draft；
- 人工批准的个人研究建议。

系统不得：

- 自动下单；
- 根据模型置信度自动计算仓位；
- 把技术进步直接等同于股东回报；
- 无价格时间点、证券身份和估值依据时输出买卖方向；
- 把公司自述当作独立验证；
- 把未解析 Forecast 计为成功；
- 用后见之明修改原 Forecast。

## 7. 建议新增正式对象及 ID

以下全部是 proposal，实施前必须经 RCP 批准：

| 对象 | ID | 说明 |
|---|---|---|
| Sector | `SEC-AI-<slug>` | AI 产业板块；避免与证券 SEC 混淆时可改 `SEG` |
| Technology | `TEC-<slug>` | 稳定技术实体 |
| Product | `PRD-<slug>` | 产品或平台 |
| Security | `INS-<market>-<ticker>` | 公司与可交易证券分离 |
| Metric | `MET-<slug>` | 指标定义，不是指标观测值 |
| Source Channel | `CHN-<slug>` | 稳定采集配置 |
| Ontology Assertion | `REL-YYYYMMDD-NNN` | 带 Evidence 的关系断言 |
| Impact Assertion | `IMP-YYYYMMDD-NNN` | 带机制的影响断言 |
| Analysis Mode | `MOD-ANL-<slug>-vN` | 版本化模式定义 |
| Analysis Run | `ANL-YYYYMMDD-NNN` | 不可变模式运行结果 |
| Forecast | `FCT-YYYYMMDD-NNN` | 可解析预测 |
| Forecast Resolution | `RES-YYYYMMDD-NNN` | 结果判定与证据 |
| Valuation Snapshot | `VAL-YYYYMMDD-NNN` | 有日期的估值输入和情景 |
| Recommendation | `REC-YYYYMMDD-NNN` | 研究建议草稿/决定 |

`SEC` 前缀与美国 SEC Adapter 容易混淆，阶段 0 人工决策应优先考虑使用 `SEG`。

## 8. 建议 RCP 清单

| RCP | 目标 | 必须在何时批准 |
|---|---|---|
| RCP-v03-001 | 产品定位、Candidate/Source 权威边界 | 任何 v0.3 编码前 |
| RCP-v03-002 | Taxonomy v2 与稳定板块 ID | Phase 1 migration 前 |
| RCP-v03-003 | 新实体 Schema 和永久 ID | Phase 1 写对象前 |
| RCP-v03-004 | Candidate SQLite 与 retention | Phase 2 写数据库前 |
| RCP-v03-005 | Source Channel、scheduler 和许可边界 | Phase 2 自动运行前 |
| RCP-v03-006 | Ontology/Impact 关系语义 | Phase 3 写 assertion 前 |
| RCP-v03-007 | Analysis Mode 与 Analysis Run 权威边界 | Phase 4 前 |
| RCP-v03-008 | Forecast、Resolution 和 calibration | Phase 5 前 |
| RCP-v03-009 | Recommendation 等级与人工批准规则 | Phase 5 前 |
| RCP-v03-010 | v0.3 数据库、备份和恢复策略 | Phase 6 发布前 |

## 9. 隐私、许可与合规

- 每个 Channel 必须记录许可/ToS/robots 检查状态和复查日期。
- 付费数据必须记录 license 和允许的存储、派生、展示范围。
- 不抓取需绕过登录或访问控制的内容。
- 原始资产默认不进入 Git。
- 个人凭证、Cookie、API token 不得写入 Markdown、Job Run 或日志。
- Candidate 摘要不得超出来源许可；需要时只保留 locator 和元数据。
- 市场数据必须记录 provider、exchange、timestamp、currency 和延迟属性。

## 10. 章程 Gate

Phase 0 只有在以下人工决定完成后才能关闭：

- [ ] 接受或修改产品定位。
- [ ] 决定 v0.2 cadence 是否与 v0.3 并行完成。
- [ ] 决定第一个 Pilot value chain。
- [ ] 决定 Universe Core 规模上限。
- [ ] 决定 Candidate store 使用 SQLite。
- [ ] 决定 Sector ID 前缀。
- [ ] 决定 Recommendation 最高权威等级。
- [ ] 批准 RCP-v03-001。
- [ ] 为其余 RCP 指定 reviewer 和计划日期。

