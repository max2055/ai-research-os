# Metadata Schema v0.3 提案（A-005）

状态：`proposed / pending RCP-v03-003 approval`
创建日期：2026-08-05
工作包：WP-101 / A-005（Schema 提案草稿，不落地代码）
依赖：`Metadata_Schema.md`（v0.2）、`02_Phase_0_1_Ontology_and_Universe.md` §4、`Taxonomy_v2_Proposal.md`（RCP-v03-002 approved）、地区范围约束（D-REGION-SCOPE）
reviewer（待）：max（按 D9，Wave 1）

> 本文件是 v0.3 Entity Schema **提案草稿**，不是已生效的 Schema。
> 按 Research_Rules / Agent Execution Protocol，永久 ID、新对象类型、Schema 变更需
> RCP-v03-003 人工批准并落地 WP-102。本提案不改动任何 v0.2 对象。
> 实现代码（Pydantic schemas）属 WP-102，本文件只定义字段与语义。

## 0. 设计原则

1. **继承 v0.2 `ManagedObjectSchema`**：所有新实体复用 `id/type/title/created_at/updated_at/schema_version/project_ids/tags/status/review_status` 公共字段；v0.2 字段不重定义。
2. **`schema_version` 升级提案为 `2`**：v0.2 对象保持 `schema_version: 1`；新 v0.3 实体用 `2`。v0.2 reader 须能**无损读取 v0.2 对象**（compat 测试强约束，Phase 0-1 §9 Gate）。
3. **永久 ID 全局唯一、parser 不歧义**（A-006 落实；本文列前缀与正则）。
4. **产业归属用 `sector_ids` 实体引用**，不再用扁平 tag 表达产业细分（RCP-v03-002 map 决定；tag 退役映射来自 `Taxonomy_v2_Mapping`）。横向维度（MAT/CUS/BM/MOAT/EV/REG/SUP/CAP/CYC/RGT）继续放 `tags`。
5. **AI 产物默认 `pending`**；所有引用 `*_ids` 仅指向已存在实体；不通过猜测填 unknown。
6. **地区优先级（D-REGION-SCOPE）落地到 Company 的地区字段与 Sector `core_company_ids` 的选用**；不限制 Schema 字段本身。
7. **Candidate/Source 边界（RCP-v03-001）保持**：本 Schema 不定义 Candidate（属 RCP-v03-004/Phase 2）；本文件只定义**正式研究对象**的扩展。

## 1. 新增正式对象类型 × 永久 ID

| 对象 | ID 形式 | type | 说明 |
|---|---|---|---|
| Sector | `SEG-<slug>` | sector | 扇区实体（D6 选 SEG） |
| Technology | `TEC-<slug>` | technology | 稳定技术实体 |
| Product | `PRD-<slug>` | product | 产品/平台 |
| Security | `INS-<market>-<ticker>` | security | 可交易证券，与 Company 分离 |
| Metric Definition | `MET-<slug>` | metric | 指标定义（非观测值） |
| Source Channel | `CHN-<slug>` | source_channel | 稳定采集配置（Phase 2 detailing） |
| Ontology Assertion | `REL-YYYYMMDD-NNN` | ontology_assertion | 带证据关系断言 |
| Impact Assertion | `IMP-YYYYMMDD-NNN` | impact_assertion | 带机制影响断言 |
| Analysis Mode | `MOD-ANL-<slug>-vN` | analysis_mode | 版本化模式定义（Phase 4） |
| Analysis Run | `ANL-YYYYMMDD-NNN` | analysis_run | 不可变运行结果（Phase 4） |
| Forecast | `FCT-YYYYMMDD-NNN` | forecast | 可解析预测（Phase 5） |
| Forecast Resolution | `RES-YYYYMMDD-NNN` | forecast_resolution | 结果判定（Phase 5） |
| Valuation Snapshot | `VAL-YYYYMMDD-NNN` | valuation_snapshot | 有日期的估值（Phase 5） |
| Recommendation | `REC-YYYYMMDD-NNN` | recommendation | 研究建议草稿（Phase 5） |

> 日期型后缀（`YYYYMMDD-NNN`）的对象仍属后续 Phase（3/4/5/6）；本提案聚焦 Phase 0-1
> 范围内要落地的：**Sector / Technology / Product / Security / Metric** 与 Company 扩展。
> Source Channel 详细字段留 Phase 2 / RCP-v03-005；Assertion/Mode/Forecast 等留后续 RCP。

## 2. 公共字段（沿用 v0.2，不重定义）

```yaml
id:
type:
title:
created_at:
updated_at:
schema_version: 2        # 新实体用 2；v0.2 对象保持 1
project_ids: []
tags: []                  # 横向维度：MAT-/CUS-/BM-/MOAT-/EV-/REG-/SUP-/CAP-/CYC-/RGT-
status:
review_status:           # pending | reviewed | rejected | superseded
```

> Sector 实体是**跨项目共用**的 Universe 基元；`project_ids` 可为空列表（公共
> Universe），不强制归属单一 Project。详见 §6 ownership 规则。

## 3. Sector Schema

```yaml
id: SEG-<slug>
type: sector
title:                     # 扇区显示名（如 "Compute Silicon"）
parent_id:                 # 父扇区 ID（可空，顶层扇区无）
definition:
in_scope: []               # 明确范围项（子类/示例）
out_of_scope: []
value_chain_position:      # 价值链位置描述
key_inputs: []             # string 列表，描述关键投入
key_outputs: []
key_metrics: []            # MET-<slug> 引用列表
core_company_ids: []       # COM-ID 列表（Core 席位，按 D-REGION-SCOPE 优先中美）
tracked_company_ids: []
source_channel_ids: []     # CHN-ID 引用（Phase 2 接入）
evidence_ids: []           # EVT-ID 列表，扇区级证据
review_status: pending
tags: []                   # 横向维度（如 REG- 供 Sector 地区敞口）
schema_version: 2
project_ids: []            # 通常空（公共 Universe）
created_at:
updated_at:
```

正则：`^SEG-[a-z0-9]+(?:-[a-z0-9]+)*$`

约束（Phase 0-1 §5 体现）：
- `core_company_ids` / `tracked_company_ids` 必须指向已存在 Company；非中美企业进 Core 须在其对象记地区与理由（D-REGION-SCOPE）。
- `parent_id` 成环检测由 validator 强制（不能自引用、不能 ancestor 链成环）。
- 扇区层级一经 reviewed，`SEG-<slug>` 永久不变；时间变化创建新 Sector 或写 `retired_at`（提议新增，见 §10）。

## 4. Company 扩展（v0.2 无损读取）

v0.2 Company 字段保留：`id/title/aliases/related_entities/evidence_ids/source_ids/status/review_status`。
新增字段（全部 optional + 默认值，保证 v0.2 对象 `schema_version=1` 可读）：

```yaml
id: COM-<slug>
type: company
# v0.2 字段（不变）
aliases: []
related_entities: []
evidence_ids: []
source_ids: []
status:
review_status:
# v0.3 新增（optional）
legal_name:
company_stage: public|private|subsidiary|state_owned|other
headquarters:                # 国家/城市；承载 D-REGION-SCOPE 主地区
region_primary:              # 新增：REG-cn | REG-us | REG-<region>；地区优先级用
sector_ids: []               # SEG-ID 引用（产业归属，替代扁平 INF-* tag）
product_ids: []              # PRD-ID
technology_ids: []           # TEC-ID
security_ids: []             # INS-ID（公司与证券分离）
coverage_tier: core|tracked|discovery
source_channel_ids: []       # CHN-ID
key_metric_ids: []            # MET-ID
region_tags: []              # 横向 REG-/SUP- 等，放 tags 即可；此字段提案为 alias
# 升级 schema_version=2 时启用
schema_version: 2            # v0.2 Company 仍 1，可读不写
```

**无损读取约束**：v0.2 Company 验证器须对所有 8 个现存 COM-* 对象通过；新字段缺失走默认（空列表 / None），不报错。WP-102 实现 commit 须含"v0.2 Company round-trip"测试项（Phase 0-1 §9）。

## 5. Security Schema（Company 与可交易证券分离）

```yaml
id: INS-<market>-<ticker>
type: security
issuer_company_id:          # COM-ID，必填
instrument_type: common_stock|adr|fund|other
ticker:
exchange:
currency:
country:
share_class:
active_from:
active_to:                  # 证券变更/退市时间明确化（不删除历史）
review_status: pending
schema_version: 2
project_ids: []              # 证券可跨项目
created_at:
updated_at:
```

正则：`^INS-[A-Z]{2,6}-[A-Z0-9.\-]+$`（market 与 ticker 不可带连字符歧义；WP-102 落地 parser，A-006 已标记 `INS-<market>-<ticker>` 的连字符歧义见 §9）。

理由（Phase 0-1 §4.3）：处理多上市地、ADR、私有公司、证券变更；Company 与 Security 分离后 `security_ids` 由 Company 引用。

## 6. Product / Technology Schema

```yaml
id: PRD-<slug> | TEC-<slug>
type: product | technology
owner_company_ids: []        # COM-ID（可多家共拥）
sector_ids: []               # SEG-ID（跨扇区时多引）
maturity:                    # MAT-* 等价描述（用 tags 承载 MAT- 维度）
introduced_at:
retired_at:
parent_id:                   # 产品/技术谱系（可空）
evidence_ids: []             # EVT-ID
review_status: pending
schema_version: 2
project_ids: []
created_at:
updated_at:
```

正则：`^PRD-[a-z0-9]+(?:-[a-z0-9]+)*$` / `^TEC-[a-z0-9]+(?:-[a-z0-9]+)**$`

Technology 实体承载 RCP-v03-002 map 决定中退役为 Technology 的 MOD-* 语义（MOD-FOUNDATION → TEC-foundation-model 等），但**历史对象 tag 不回填**（R1）。

## 7. Metric Definition Schema

```yaml
id: MET-<slug>
type: metric
name:
definition:
unit:
frequency:
scope: sector|company|product|technology|security
owner_entity_ids: []         # 按 scope 引用对应实体 ID
preferred_source_types: []  # 优先来源类型（source_type 枚举）
comparison_limits:          # 跨公司/跨期比较口径限制（自由文本或结构化）
review_status: pending
schema_version: 2
project_ids: []
created_at:
updated_at:
```

正则：`^MET-[a-z0-9]+(?:-[a-z0-9]+)*$`

**关键约束**：Metric 是 **定义**，不是观测值。指标观测值（财年、口径、Source、period/as_of）由 Source/Event 承载；不得覆盖 Metric 定义（Phase 0-1 §4.5）。WP-102 实现须拒绝"观测值字段进入 Metric 定义对象"的写入。

## 8. Source Channel Schema（Phase 2 detailing，本提案只占 ID 与骨架）

```yaml
id: CHN-<slug>
type: source_channel
title:
config_kind:                 # rss|github_release|arxiv|sec|custom
allowlist: []                # 查询/路径白名单（硬上限）
rate_limit:
license_status:              # robots/ToS/许可复查状态
last_checked:
retention_days:
review_status: pending
schema_version: 2
project_ids: []
created_at:
updated_at:
```

正则：`^CHN-[a-z0-9]+(?:-[a-z0-9]+)*$`。详细字段与 Candidate 提升关联留 RCP-v03-004/005。

## 9. 永久 ID 冲突与 parser 歧义（A-006 落地要点，§1/§5 已标出）

| 风险 | 状态 | 处理 |
|---|---|---|
| `MOD-ANL-` 双段前缀（`MOD-` vs `MOD-ANL-`）| 易混 | WP-102 parser 锚定 `^MOD-ANL-`；Analysis Mode 不复用 `MOD-` 单段前缀 |
| `INS-<market>-<ticker>` 连字符歧义 | parser 须切分 | WP-102 用定长 `market`（2–6 字母大写）+ 剩余为 ticker；ticker 内连字符允许 |
| `MET-` 与 "metric" 语义 | 无冲突 | v0.2 无 `MET-` 对象（A-006 扫描确认）；`MET-` 唯一表 Metric 定义 |
| `ANL-` (Analysis Run) vs `MOD-ANL-` (Analysis Mode) | 易读混 | WP-102 ID parser 用前缀严格匹配；文档显式区分 |
| `REL-` (Ontology Assertion) vs Report/Review `R-*` | 无冲突 | `REL-` 唯一表 Ontology Assertion；v0.2 `REV-` 表 Review |
| 日期型 ID `YYYYMMDD-NNN` 与日期字段 | parser 须锚定 `id:` 行 | WP-102 ID parser 只从 frontmatter `id:` 读取 |

A-006 全文见 `00_System/ID_Conflict_Analysis.md`（WP-101 同批产出）。

## 10. 共享行为规则

- **新建实体默认 `review_status: pending`**；reviewed 需人工。
- **不覆盖永久 ID**：`retired_at` / `superseded_by` 记录退役，不删除。
- **sector_ids refusal**：被引用的 Sector 必须存在；validator 拒绝悬空引用（Phase 0-1 §5）。
- **回滚（Phase 0-1 §11）**：新 Schema 在独立 migration 引入；migration 前 Git commit + 对象 hash manifest；可删新实体回滚；旧 Tag 映射保留兼容窗口。
- **YAML round-trip**：Pydantic + ruamel.yaml 保留人工正文、顺序、注释（Agent Execution Protocol §6 Schema）。

## 11. 与 Taxonomy v2 一致性

- `sector_ids` 引用的 Sector 即 Taxonomy v2 的 13 个 L1 扇区（RCP-v03-002）。
- 横向维度放 `tags`：保持 keep 的 MAT/CUS/BM/MOAT/EV + 新增 REG/SUP/CAP/CYC/RGT。
- 退役产业 tag（INF-GPU 等）的语义由 `TEC-<slug>` Technology 实体承载（R3）；v0.2 历史 tag 不回填（R1），新对象用 `technology_ids` 引用。
- SRV-DATA-LABELING 归属（R6）：默认归 Services 扇区；本 Schema 不预设子扇区字段，由 Sector parent_id 层级表达。

## 12. 验收（RCP-v03-003 批准门槛）

- [ ] Sector/Security/Product/Technology/Metric 五个 Schema 字段完整、正则明确
- [ ] 前 14 个新对象类型 × 永久 ID 表齐全（Phase 0-1 范围 5 个详描，其余占位）
- [ ] v0.2 Company 无损读取测试可描述（不含 fixture 回填，仅 round-trip）
- [ ] 与 A-006 ID 冲突分析一致
- [ ] 与 RCP-v03-002 Taxonomy v2 扇区一致
- [ ] 候选对象类型（Assertion/Analysis/Forecast/Valuation/REC）列占位，详细留后续 RCP
- [ ] Region 优先级（D-REGION-SCOPE）在 Company/Schema 字段落点明确

## 13. 不做的事

- 不落代码（Pydantic schemas 属 WP-102）。
- 不创建任何 Sector/Technology/Product/Security/Metric 实体（属 WP-120 / WP-102 后续）。
- 不定义 Candidate（RCP-v03-004）、Ontology/Impact 关系语义（RCP-v03-006）、Analysis Mode 契约（RCP-v03-007）、Forecast/REC（RCP-v03-008/009）的完整字段——本文仅 ID 占位。
- 不改动任何 v0.2 对象的 frontmatter。

## 14. 状态

本提案 + A-006（ID 冲突）+ A-007（Migration 设计）共同构成 RCP-v03-003 输入。
RCP-v03-003 一旦批准，新 Entity Schema 与永久 ID 体系即生效，WP-102 起落地 Pydantic
schemas、validator、index、repository transaction。