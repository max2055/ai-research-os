# v0.3 Master Backlog 与实施波次

状态：`proposed`  
规则：本文件是执行索引；任务细节以各 Phase 文件为准。Agent 不得只读本表就开工。

## 1. 状态枚举

- `proposed`：尚未批准；
- `ready`：依赖/RCP/owner/Gate 已明确；
- `in_progress`：已分配唯一 owner；
- `verification`：实现完成，正在全仓库/真实 Gate；
- `blocked`：有明确外部/人工阻断；
- `completed`：Definition of Done 全部满足；
- `cancelled`：有人工作出决定和原因。

初始状态：所有 v0.3 工作包为 `proposed`。

## 2. 关键路径

```text
WP-000 Baseline
→ WP-010 Governance
→ WP-100 Taxonomy/Schema
→ WP-120 Pilot Universe
→ WP-200 Candidate Store/Channels
→ WP-230 Discovery/Scoring/Daily Brief
→ WP-300 Impact Schema/Direct
→ WP-320 Multi-hop/Field Gate
→ WP-400 Mode Contract/Runner
→ WP-430 Mode Field Gate
→ WP-500 Forecast/Valuation
→ WP-530 Recommendation/Resolution
→ WP-600 Unified Product
→ WP-630 30-day Pilot/Release
```

## 3. Wave 0：Baseline 与治理

| WP | 包含任务 | 交付 | 依赖 | 状态 |
|---|---|---|---|---|
| WP-000 | baseline audit | v0.2 commit/object/test/release snapshot | 无 | proposed |
| WP-001 | v0.2 cadence completion | 真实 Weekly/Monthly/final decision | 日期和研究者 | blocked until dates |
| WP-010 | A-001 | RCP-v03-001 产品/Candidate 边界 | WP-000 | proposed |
| WP-011 | charter decisions | Pilot、Core 上限、Sector ID、Recommendation ceiling | WP-010 | proposed |
| WP-012 | RCP schedule | RCP-v03-002～010 owner/date | WP-010 | proposed |
| WP-013 | engineering ADR set | Candidate DB、store boundaries、version strategy | WP-010 | proposed |

Wave 0 Gate：RCP-v03-001 获批，所有关键人工选择记录，后续 WP 有 owner 和 stop condition。

## 4. Wave 1：Taxonomy、Schema、Universe

| WP | 包含任务 | 可并行 | 主要交付 | 状态 |
|---|---|---|---|---|
| WP-100 | A-002～004 | 否 | Taxonomy audit/mapping/v2 RCP | proposed |
| WP-101 | A-005～007 | 与 WP-100 设计协调 | Schema/ID/migration proposal | proposed |
| WP-102 | A-008～010 | Product/Metric 可拆子包 | Entity schemas/services | proposed |
| WP-103 | A-011～012 | 在 Schema 稳定后 | Relation assertion + ontology export | proposed |
| WP-104 | A-013～015 | index/UI 可并行 | Registry CLI/index/dashboard | proposed |
| WP-120 | A-016 | 按 Sector 分包 | 30–50 Core Company Universe | proposed |
| WP-121 | A-017 | 按关系类型分包 | 100–200 relation proposals | proposed |
| WP-122 | A-018～019 | 否 | coverage metrics + field review | proposed |
| WP-123 | A-020 | 否 | migration/recovery/acceptance | proposed |

并行限制：

- WP-120 可按 Sector 分配研究 Agent，但 Company ID registry 由一个 integration owner 维护；
- WP-121 可按 supplier/competition/product ownership 分包，但 predicate 定义不可并行修改；
- WP-102 未稳定前不要做 WP-104 UI。

## 5. Wave 2：Candidate Intelligence

| WP | 包含任务 | 主要交付 | 状态 |
|---|---|---|---|
| WP-200 | B-001～004 | RCP + Candidate DB ADR/migration | proposed |
| WP-201 | B-005～007 | Channel Registry + discovery orchestration | proposed |
| WP-210 | B-008～013 | P0 adapters；每个 Adapter 独立子包 | proposed |
| WP-220 | B-014～017 | dedup/entity/sector/scoring | proposed |
| WP-230 | B-018～020 | Candidate Queue + promote transaction | proposed |
| WP-231 | B-021～022 | launchd + Daily Brief | proposed |
| WP-232 | B-023～024 | metrics/health/secret redaction | proposed |
| WP-240 | B-025～026 | 14-day real Pilot + acceptance | proposed |

Adapter 子包接口冻结后可以并行。任何新 Adapter 先有明确 Channel、allowlist、rate、许可和
fixture，不允许以“先抓到再治理”为理由跳过。

## 6. Wave 3：Impact

| WP | 包含任务 | 主要交付 | 状态 |
|---|---|---|---|
| WP-300 | C-001～003 | RCP、Schema、rule map | proposed |
| WP-301 | C-004～005 | direct impact + mechanism validator | proposed |
| WP-310 | C-006～010 | temporal multi-hop/conflict/confidence | proposed |
| WP-311 | C-011～012 | spec/renderer/review | proposed |
| WP-312 | C-013～016 | index/CLI/UI/report integration | proposed |
| WP-320 | C-017～018 | metrics + 20-event field Gate | proposed |
| WP-321 | C-019～020 | benchmark/recovery/acceptance | proposed |

先通过 direct impact Field Gate，再决定是否把 2–3 hop proposal 设为 active。

## 7. Wave 4：Analysis Modes

| WP | 包含任务 | 主要交付 | 状态 |
|---|---|---|---|
| WP-400 | D-001～004 | RCP、Mode/Run Schema、contract | proposed |
| WP-401 | D-005～009 | registry、resolver、runner transaction | proposed |
| WP-410 | D-010 | 9 mode definitions；可按 mode 分包 | proposed |
| WP-411 | D-011～013 | compare、Red Team、discovery sandbox | proposed |
| WP-412 | D-014～016 | CLI/UI/promotion proposal | proposed |
| WP-420 | D-017～018 | evaluator/metrics | proposed |
| WP-430 | D-019～020 | 10-case field Gate/recovery | proposed |

所有 Mode 子包必须共用同一 output contract，不得各自创造不兼容的 Facts/Inference 字段。

## 8. Wave 5：Forecast 与 Decision

| WP | 包含任务 | 主要交付 | 状态 |
|---|---|---|---|
| WP-500 | E-001～006 | RCP + Forecast/Resolution/Valuation/REC Schema | proposed |
| WP-501 | E-007～010 | forecast lifecycle/resolution | proposed |
| WP-510 | E-011～013 | valuation/scenario/recommendation workflow | proposed |
| WP-511 | E-014～015 | supersession/calibration | proposed |
| WP-512 | E-016～018 | CLI/UI/alerts | proposed |
| WP-520 | E-019～021 | license + 10 forecast + 3 company Pilot | proposed |
| WP-530 | E-022～023 | natural resolution + acceptance | future-date dependent |

WP-530 不能用回填或合成 outcome 提前完成。

## 9. Wave 6：统一产品与发布

| WP | 包含任务 | 主要交付 | 状态 |
|---|---|---|---|
| WP-600 | F-001～003 | IA/read model/Industry Home | proposed |
| WP-601 | F-004～006 | Sector/Company/Candidate UI | proposed |
| WP-602 | F-007～009 | Impact/Analysis/Decision UI | proposed |
| WP-603 | F-010～011 | Operations/Health | proposed |
| WP-610 | F-012～014 | profile/SLO/security | proposed |
| WP-611 | F-015～018 | license/backup/recovery/migration | proposed |
| WP-612 | F-019～020 | runbook/limitations | proposed |
| WP-620 | F-021～022 | 30-day Pilot/resolutions | future-date dependent |
| WP-630 | F-023～025 | release check/human decision/tag | WP-620 | proposed |

## 10. 建议首批派发顺序

在用户批准 v0.3 后，按以下顺序逐包派发，避免一次给 Agent 过大范围：

1. WP-000：只读 baseline audit。
2. WP-010：产品与 Candidate 边界 RCP 草稿。
3. WP-011：列出需用户选择的明确选项，不编码。
4. WP-100：Taxonomy v1 audit/mapping。
5. WP-101：Schema/ID/migration proposal，不 apply。
6. 用户批准 RCP-v03-002/003。
7. WP-102：Entity schemas 垂直实现。
8. WP-103：关系 assertion 与 export。
9. WP-120：按 Pilot Sector 建立 Universe。
10. WP-122：真实抽检后再进入 Candidate Pipeline。

## 11. Backlog 维护规则

- 只有 integration owner 修改本文件状态；
- Agent 在 handoff 中建议状态，但不自行标记整个 Phase completed；
- `blocked` 必须写 blocker、owner、解除条件和下一检查日；
- future-date Gate 保持明确日期，不能提前回填；
- 新任务用现有 Phase 前缀追加，不重编号已发布任务；
- 取消任务保留 ID 和理由；
- 任务拆分后原 ID 变 parent，不复用；
- 每次 Weekly review 更新完成、阻断、风险、coverage 和下周 WP；
- 每次 Monthly review评估是否扩大 Universe 或改变存储，不由 Agent 自动决定。

## 12. 全局风险登记

| 风险 | 早期信号 | 缓解 | Owner |
|---|---|---|---|
| Universe 扩张过快 | coverage 下降、stale 增加 | Core 上限、分批 Gate | researcher |
| Candidate 噪声 | Top-N precision 下降 | Channel/评分/去重 review | ingestion owner |
| 数据许可 | restricted/unknown 增加 | Channel enable Gate | researcher/legal |
| Ontology 过度建模 | predicate 频繁变更 | 先 Pilot、append-only version | ontology owner |
| 因果幻觉 | 多跳编辑率高 | direct-first、mechanism review | impact owner |
| 模式同质化 | 输出差异只在措辞 | 固定问题/禁区/field rubric | analysis owner |
| 投资过度结论 | 缺估值仍给方向 | Recommendation validator | decision owner |
| 后见偏差 | Forecast 被改写 | immutable Forecast + Resolution | forecast owner |
| SQLite 瓶颈 | lock/p95 超 Gate | profile 后再评估 PostgreSQL | platform owner |
| iCloud 冲突 | conflicted copy/hash 问题 | 单写者、Git remote、离机资产备份 | owner |
| Agent scope drift | 无 RCP 改 Schema | WP contract/stop conditions | integration owner |
| 成本失控 | model/API cost 超预算 | per-channel/run budget | operations owner |

## 13. 决策日志模板

每个关键选择在对应 RCP/ADR 中记录：

```text
Decision ID:
Date:
Question:
Options considered:
Decision:
Reason:
Evidence/benchmark:
Consequences:
Migration:
Rollback:
Reviewer:
Revisit trigger/date:
```

### 13.1 已记录决策

#### D1 产品定位（2026-08-05）
- Decision ID: D1
- Date: 2026-08-05
- Question: 是否接受 v0.3 产品定位（AI Industry Intelligence & Decision OS）？
- Options considered: 接受 / 修改目标闭环 / 拒绝
- Decision: 接受。在 v0.2 Evidence Kernel 之上建设 Universe/每日情报/Ontology/Impact/Analysis Mode/Forecast/Recommendation，保留 v0.2 全部继承原则。
- Reason: 现有 single-topic 边界无法承载 AI 全产业链；目标闭环见 Roadmap §1。
- Evidence/benchmark: WP-000_Baseline_Audit.md（v0.2 基线 166 对象、0 error）。
- Consequences: 启用 v0.3 全阶段规划；Charter/Schema/ID 推进需逐项 RCP 批准。
- Migration: 无数据迁移；治理边界变更由 RCP-v03-001 承载。
- Rollback: 撤销 RCP-v03-001 即回退定位（不影响既有对象）。
- Reviewer: max
- Revisit trigger/date: 30-day Pilot Gate / v0.3 发布决定（D12）。

#### D2 cadence 先后（2026-08-05）
- Decision ID: D2
- Decision: 并行推进。WP-001（2×Weekly + 1×Monthly + ACT-20260729-009 + 最终发布决定）保持日期阻塞；v0.3 只读/文档型 WP 先行，不争用同一人审时段。
- Reviewer: max
- Revisit trigger/date: v0.2 最终发布时或 cadence 出现与 v0.3 争用时。

#### D3 第一 Pilot value chain（2026-08-05）
- Decision ID: D3
- Decision: AI Compute Infrastructure Chain（半导体材料与设备 → 制造/封装/测试 → GPU/ASIC → HBM/DRAM/Storage → Server/Network/Optics → Datacenter/Power/Cooling → Cloud AI Infra → Foundation Model Demand）。
- Reason: 多板块、多公司、多跳关系；原始来源相对丰富；供给/成本/产能/资本开支机制可观察。
- Consequences: Universe 首批围绕此链建 Core；第二 Pilot 再覆盖 Model-Agent-Enterprise。
- Reviewer: max
- Revisit trigger/date: 第一 Pilot Gate 后扩 Universe 时（D10）。

#### D4 Universe Core 上限（2026-08-05）
- Decision ID: D4
- Decision: Pilot Core 规模 30–50 家公司；未经批准不得扩大。
- Reviewer: max
- Revisit trigger/date: 每个 Pilot Gate 后评估（D10）。

#### D5 Candidate store（2026-08-05）
- Decision ID: D5
- Decision: 使用 SQLite 作为可重建 operational store，保存高频候选与调度状态；非事实源。须提供 Schema version、deterministic migration、export/import、backup/snapshot、retention、Candidate 提升为 Source 的永久关联。
- Reviewer: max
- Revisit trigger/date: 量化瓶颈出现时评估 PostgreSQL（D11）。

#### D6 Sector ID 前缀（2026-08-05）
- Decision ID: D6
- Decision: `SEG-<slug>`。避免与美国 SEC Adapter/披露混淆。
- Reviewer: max
- Revisit trigger/date: 引入 Security 对象并需区分监管实体时复核。

#### D7 Recommendation 最高权威等级（2026-08-05）
- Decision ID: D7
- Decision: Recommendation 最高为人工批准的个人研究建议；不得自动执行、不自动下单、不按模型置信度自动计算仓位。
- Reviewer: max
- Revisit trigger/date: Phase 5（RCP-v03-009）细化等级时。

#### D8 批准 RCP-v03-001（2026-08-05）
- Decision ID: D8
- Decision: 批准 RCP-v03-001（proposed → approved）。产品边界 + Candidate/Source 权威边界生效。
- Reviewer: max
- Revisit trigger/date: 实施发现边界不可行时提修改 RCP。

#### D9 RCP-v03-002~010 排期（2026-08-05）
- Decision ID: D9
- Decision: 按默认 Wave 排期（002/003 Wave1；004/005 Wave2；006 Wave3；007 Wave4；008/009 Wave5；010 Wave6）。reviewer 统一 max；计划日期在对应阶段开始前滚动落定。
- Reviewer: max
- Revisit trigger/date: 任一 Wave 开始前排当个 RCP 并记录日期。

#### R1-R5 Taxonomy v2 边界项（2026-08-05，ref: RCP-v03-002）
- Decision ID: WP-100-R1..R5
- Date: 2026-08-05
- Question: Taxonomy v2 的 5 个边界争议（见 A-002 §5）。
- Options considered: per item（Mapping §5 / Proposal §6）。
- Decision:
  - R1 历史 tag 不回填，保留旧 tag；mapping 表提供映射；补 SEG 关系时人工逐批核。
  - R2 APP-CODING keep 为 tag，归 Enterprise Applications 下 AI Developer Tooling 子域。
  - R3 MOD-* 6 个全 map 到 Models 扇区下 Technology 实体。
  - R4 INF-CLOUD-AI 归 Cloud & AI Infrastructure；边界=云端模型平台/推理服务。
  - R5 INF 父类聚合 tag deprecate，历史沿用 R1 不回填。
  - R6 SRV-DATA-LABELING 默认归 Services，RCP-v03-002 现场定。
- Reason: 见 A-002 审计（usage 41/93、INF 层近废）与 Phase 0-1 §3 扇区草案；保持"产业细分由实体表达"+"不自动改写历史"。
- Evidence/benchmark: `Taxonomy_v2_Mapping.md`、`Taxonomy_v2_Proposal.md`、`research-os validate` 0 error。
- Consequences: RCP-v03-002 草案备齐待 max 批准；WP-101 Schema 须与 Taxonomy v2 一致。
- Migration: 不回填（R1）；新对象用 SEG-ID；WP-123 落实。
- Rollback: 保留 v0.1 Taxonomy 与兼容窗口（Phase 0-1 §11）。
- Reviewer: max
- Revisit trigger/date: RCP-v03-002 最终审批时；与 WP-101 Sector Schema 核对时。

#### RCP-v03-002 批准（2026-08-05）

- Decision ID: RCP-v03-002-approval
- Date: 2026-08-05
- Decision: 批准 RCP-v03-002（proposed → approved）。Taxonomy v2 与稳定板块 ID 体系生效：13 个 L1 扇区作 Sector 实体（SEG-ID）、5 个横向维度扩展前缀（REG/SUP/CAP/CYC/RGT）、v1→v2 权威映射表、边界项 R1–R5 整体接受。
- Reason: A-002 审计 + A-003 草案备齐，边界项已由 reviewer max 拍板。
- Effective date: 2026-08-05。
- Consequences: Taxonomy v2 成为权威；v0.1 Taxonomy 标注 superseded 但保留为历史参考；v0.2 历史 tag 不回填（R1）；后续 WP-101 Schema 须与 Taxonomy v2 一致。SRV-DATA-LABELING 归属（R6）在 WP-101/Schema 阶段现场定。
- Reviewer: max
- Revisit trigger/date: 与 WP-101 Sector Schema 核对；任一扇区边界实施遇阻时提修改 RCP。

#### 地区优先级范围约束（2026-08-05）

- Decision ID: D-REGION-SCOPE
- Date: 2026-08-05
- Question: Universe 研究对象的地区范围？（上下文：在 RCP-v03-002 批准后，开 WP-101 前）
- Options considered: 仅中美 / 中美为主其他为辅 / 全球无优先级。
- Decision: 研究对象以中国、美国 AI 企业为主，其他地区的重点企业为辅。
- Reason: 研究者明确范围；中美当前是 AI 产业最具区分度的市场，其他地区保留关键节点（卡位/稀缺供给）。
- Evidence/benchmark: 研究者陈述（2026-08-05）；`02_Phase_0_1_...md` §6.1。
- Consequences: Core 席位优先中美；非中美企业进 Core 须写明价值链区分度理由（如 ASML/TSMC/SK hynix）。`REG-` 地区维度按国别细分中美、其他归 Country/Region 级。D10（扩 Universe Gate）复核地区覆盖平衡。
- Migration: 无；`REG-` 前缀已由 RCP-v03-002 批准承载该维度。
- Rollback: 不适用（范围约束，可在 D10 Gate 重新评估）。
- Reviewer: max
- Revisit trigger/date: WP-120 Universe 建设时；D10 扩 Universe Gate 时评估地区平衡。

