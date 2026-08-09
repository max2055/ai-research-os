# Phase 0–1：产品重定义、AI Taxonomy、Ontology 与 Universe

状态：`completed`（2026-08-06，Phase 1 CLOSED）  
建议周期：4–7 周  
前置：v0.2 baseline 通过；RCP-v03-001～003 获批  

## 1. 阶段目标

把当前围绕企业软件专题的标签和 8 家公司，升级为可扩展的 AI 产业地图：

- 稳定板块和子板块；
- Company 与 Security 分离；
- Product、Technology、Metric 成为正式实体；
- 30–50 家 Core Company Universe；
- 可审计的供应、客户、竞争、依赖和替代关系；
- 所有后续采集 Channel 都能绑定明确实体和研究范围。

## 2. 非目标

- 本阶段不自动抓取每日新闻；
- 不实现因果传播分数；
- 不引入 Neo4j；
- 不创建没有 Source/Evidence 的权威关系；
- 不覆盖所有 AI 公司；
- 不把股票代码当作 Company 永久 ID；
- 不因建立公司列表而自动形成投资观点。

## 3. Taxonomy v2 草案

建议顶层：

| Level 1 | Level 2 示例 |
|---|---|
| Semiconductor Materials & Equipment | wafer、photoresist、gas、EDA、lithography、etch、deposition、inspection |
| Foundry, Packaging & Test | foundry、advanced packaging、OSAT、substrate |
| Compute Silicon | GPU、AI ASIC、CPU、edge accelerator |
| Memory & Storage | HBM、DRAM、NAND、enterprise storage |
| Server, Network & Interconnect | server、switch、optical、interconnect、rack |
| Datacenter Infrastructure | power、cooling、UPS、energy、construction |
| Cloud & AI Infrastructure | cloud compute、model platform、inference service |
| Models | foundation、reasoning、multimodal、small/open models |
| Data & AI Development | data、training、inference、evaluation、security、agent runtime |
| Enterprise Applications | CRM、ERP、ITSM、HCM、security、analytics、vertical |
| Consumer Applications | assistant、content、education、search、commerce |
| Services | consulting、integration、managed service、data service |
| Physical AI | robotics、autonomous driving、industrial/edge AI |

横向维度继续使用并扩展：成熟度、客户、商业模式、护城河、事件类型、地区、供应风险、
资本强度、周期属性、监管敏感度。

必须先建立 Taxonomy mapping，保证 v0.1 历史 tag 不被静默改义。

## 4. Entity Schema 草案

### 4.1 Sector

```yaml
id: SEG-<slug>
type: sector
parent_id:
definition:
in_scope: []
out_of_scope: []
value_chain_position:
key_inputs: []
key_outputs: []
key_metrics: []
core_company_ids: []
tracked_company_ids: []
review_status: pending
```

### 4.2 Company

扩展现有 Company：

```yaml
id: COM-<slug>
legal_name:
company_stage: public|private|subsidiary|state_owned|other
headquarters:
sector_ids: []
product_ids: []
technology_ids: []
security_ids: []
coverage_tier: core|tracked|discovery
source_channel_ids: []
key_metric_ids: []
related_entities: []
evidence_ids: []
review_status: pending
```

### 4.3 Security

```yaml
id: INS-<market>-<ticker>
type: security
issuer_company_id:
instrument_type: common_stock|adr|fund|other
ticker:
exchange:
currency:
country:
share_class:
active_from:
active_to:
review_status: pending
```

Company 和 Security 必须分离，以处理多上市地、ADR、私有公司和证券变更。

### 4.4 Product / Technology

```yaml
id: PRD-<slug> | TEC-<slug>
type: product | technology
owner_company_ids: []
sector_ids: []
maturity:
introduced_at:
retired_at:
evidence_ids: []
review_status: pending
```

### 4.5 Metric Definition

```yaml
id: MET-<slug>
type: metric
name:
definition:
unit:
frequency:
scope: sector|company|product|technology|security
owner_entity_ids: []
preferred_source_types: []
comparison_limits:
review_status: pending
```

指标观测值应保存 period、as_of、unit、currency、Source ID 和口径，不覆盖 Metric 定义。

## 5. Ontology Assertion 草案

不能继续仅用 `related_entities` 表示所有关系。建议增加 assertion：

```yaml
id: REL-YYYYMMDD-NNN
type: ontology_assertion
subject_id:
predicate: SUPPLIES|CUSTOMER_OF|COMPETES_WITH|SUBSTITUTES|COMPLEMENTS|
  DEPENDS_ON|ENABLES|CONSTRAINS|OWNS|PARTNERS_WITH|PRODUCES|USES
object_id:
valid_from:
valid_to:
as_of:
evidence_ids: []
source_ids: []
confidence:
scope:
qualifiers: {}
review_status: pending
```

约束：

- 关系方向必须明确定义；
- subject/object 必须存在；
- `COMPETES_WITH` 等对称关系只能由 service 生成确定性反向派生，不复制权威对象；
- 时间变化创建新 assertion 或关闭旧 assertion，不覆盖历史；
- 关系存在与影响强度分开；
- 任何 reviewed assertion 至少有一个 reviewed Evidence 或经过核验的 Source；
- 公司营销中的客户/伙伴关系只证明“公司披露了关系”，不得自动证明收入重要性。

## 6. Universe 选择方法

### Core

- 每日跟踪；
- 对价值链或投资研究有高区分度；
- 5–10 个稳定 Channel；
- 完整 Company、Product、Technology、Metric 和关键关系；
- 每月至少一次覆盖复盘。

### Tracked

- 每周或事件触发；
- 2–5 个 Channel；
- 基础 Company profile 和主要关系；
- 季度覆盖复盘。

### Discovery

- 只保留身份、板块、少量关系和候选来源；
- 不承诺持续覆盖；
- 不计入 coverage completeness。

Pilot Core 建议 30–50 家，上限未经人工批准不得扩大。

### 6.1 地区优先级（范围约束，reviewer：max，2026-08-05）

研究对象以**中国、美国的 AI 企业为主**，其他地区（欧洲、日韩、东南亚、中东等）
的重点企业为辅。

落点：

- **Core 席位优先给中美企业**；其他地区企业进入 Core 需对价值链或投资研究有明确
  区分度（如关键卡位、稀缺供给、不可替代关系），否则归 Tracked/Discovery。
- **REG- 地区维度**（RCP-v03-002 已批）记录每个 Core/Tracked 企业的地区归属与
  监管敞口；中美企业按国别细分（REG-cn / REG-us），其他地区归 Country/Region 级。
- 不等于排除其他地区：当某非中美企业在价值链中是关键节点（如 ASML、TSMC、SK
  hynix 控制 HBM/Foundry Card）时，仍进入 Core，理由写入 Sector `core_company_ids`。
- 不改变 Schema/Taxonomy/ID 语义；`REG-` 前缀已承载该维度，无需新 RCP。
- 该约束在 Phase 0-1 Pick Lobby 选取与 WP-120 Universe 建设时执行；D10（扩
  Universe Gate）复核时一并评估地区覆盖平衡。

## 7. 工作包

| ID | 任务 | 建议修改路径 | 交付与验收 |
|---|---|---|---|
| A-001 | 起草并批准产品边界 RCP | `05_Research/Reviews/Proposals/` | RCP-v03-001 有人工决定 |
| A-002 | Taxonomy v1 使用审计 | `00_System/Taxonomy_v2_Mapping.md` | 每个旧 tag 有 keep/map/deprecate 决定 |
| A-003 | Taxonomy v2 proposal | `00_System/Taxonomy_v2_Proposal.md` | 定义、边界、示例、冲突、迁移齐全 |
| A-004 | 批准 Taxonomy RCP | Proposals | 一级/二级分类人工批准 |
| A-005 | 新 Entity Schema proposal | `00_System/Metadata_Schema_v0.3_Proposal.md` | Sector/Security/Product/Technology/Metric 完整 |
| A-006 | 永久 ID 冲突检查 | domain/schema tests | 前缀唯一且 parser 不歧义 |
| A-007 | Migration 设计 | `00_System/Migration_Guide_v0.3.md` | dry-run、backup、apply、rollback |
| A-008 | 实现 Sector Schema/Repository | `src/research_os/schemas/` | round-trip、validation、index tests |
| A-009 | 扩展 Company Schema | schemas/services | v0.2 Company 无损读取 |
| A-010 | 实现 Security/Product/Technology/Metric | schemas/services | CRUD draft、review、index 一致 |
| A-011 | 实现 Ontology Assertion Schema | schemas/ontology | 时间、Evidence、predicate validation |
| A-012 | 扩展 ontology export | `services/ontology.py` | 新节点/边 deterministically export |
| A-013 | 新增 entity index | `services/indexing.py` | global/project/sector index 可重建 |
| A-014 | Universe Registry CLI | `cli.py`, services | list/status/check/coverage；默认只读 |
| A-015 | Company/Sector Dashboard | `ui/app.py` | 板块→公司→产品→Evidence ≤3 clicks |
| A-016 | 建立 Pilot Core Universe | `02_Knowledge/` | 30–50 Company，全部 pending 起步 |
| A-017 | 建立首批关系 | Ontology Assertions | 100–200 条候选，人工抽检后审核 |
| A-018 | Universe coverage metrics | metrics | identity/source/relationship completeness |
| A-019 | 真实人审 Gate | review packet | 10 Company + 30 relation 抽检 |
| A-020 | 阶段验收与恢复演练 | acceptance/recovery docs | clean clone、migration rollback 通过 |

## 8. 建议 CLI

```text
research-os universe list [--tier core] [--sector SEG-ID]
research-os universe status [--company COM-ID]
research-os universe coverage [--sector SEG-ID]
research-os entity draft --type sector|company|security|product|technology|metric
research-os relations propose --spec <json>
research-os relations list --subject <ID> --as-of <date>
research-os relations review ...
research-os ontology export|impact ...
```

新写命令继续 dry-run；正式关系必须走通用 Review Decision 或经批准的专用 review。

## 9. 测试要求

### Unit

- 每个 Schema 的合法/非法元数据；
- ID parser 和前缀冲突；
- 对称、反向和时间关系规则；
- v0.2 Company 兼容；
- Taxonomy mapping；
- coverage 计算。

### Integration

- migration dry-run/apply/rollback；
- entity create→review→index→ontology export；
- relation Evidence 缺失时拒绝 reviewed；
- 多 Project 和多 Sector 复用；
- stale/expired assertion；
- Dashboard 页面和 API。

### Field Gate

- 10 家 Core Company 身份、证券、板块和来源人工核验；
- 30 条关系逐条检查 predicate、方向、时间和 Evidence；
- 至少 10 条供应链、5 条竞争、5 条依赖、5 条产品归属、5 条客户/伙伴；
- 错误率、编辑率和 unknown 分类记录到 review packet。

## 10. Gate

- [ ] RCP-v03-001～003 已批准。
- [ ] v0.1 历史对象迁移无语义漂移。
- [ ] 8–10 个 Pilot 板块定义明确。
- [ ] 30–50 家 Core Company 注册，身份无重复。
- [ ] Company 与 Security 分离。
- [ ] Product/Technology/Metric 可独立引用。
- [ ] 100+ 关系 assertion 可导出，30 条通过真实人审。
- [ ] 0 validation error；0 index drift。
- [ ] coverage ≥80%；测试总覆盖率不低于当前 80% Gate。
- [ ] migration rollback 和 clean-clone recovery 通过。

## 11. 回滚

- 新 Schema 必须在独立 migration 中引入；
- migration 前记录 Git commit 和对象 hash manifest；
- 新派生 index 可以直接删除重建；
- 新 entity 未被 reviewed Report 引用前可保留为 pending 并停止扩展；
- Taxonomy 旧 tag 在至少一个版本周期内保留 compatibility mapping；
- 不允许通过删除历史 tag 或 ID 完成回滚。

