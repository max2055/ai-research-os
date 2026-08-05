# Rule Change Proposal RCP-v03-002

Proposal ID：RCP-v03-002

状态：approved（2026-08-05，reviewer：max）

创建日期：2026-08-05

提议人：max（草稿由 Agent 按 v0.3 规划整理）

## Target

受影响的规则、Taxonomy、Agent 边界：

- 替换/升级 `00_System/Taxonomy.md`（v0.1）为 Taxonomy v2
- `02_Phase_0_1_Ontology_and_Universe.md` §3 扇区草案落为正式 Taxonomy
- `00_System/Taxonomy_v2_Mapping.md`（A-002 审计）作为 v1→v2 权威映射
- `00_System/Taxonomy_v2_Proposal.md`（A-003 草案）作为 v2 内容
- Agent 边界：不变（Agent 仍可提议 tag/实体，不自动批准；Sector SEG-ID 创建仍需 RCP-v03-003）

## Observed problem

只记录可引用的失败、warning、返工或研究质量问题：

- v0.1 Taxonomy 定义 93 个 tag，实际使用 41 个，53 个未用（A-002 审计 `Taxonomy_v2_Mapping.md` §2）。
- 整个 INF-* 基础设施层（24 个定义）近乎零使用，唯一在用 `INF-CLOUD-AI` 跨层歧义。
- v0.1 用扁平 tag 表达产业细分（INF-GPU/APP-CRM），与 v0.3 Sector+Technology/Product 实体体系不兼容；不带实体引用的产业归属无法支撑跨板块影响分析。
- 横向维度（MAT/CUS/BM/MOAT/EV）是健康核心，但缺地区、供应风险、资本强度、周期、监管敏感度 5 个 v0.2 已需要的维度。
- `APP-CODING`（PRJ-002 主线，30 次）在 v0.1 位置偏弱，需明确归属。

## Evidence

- Metrics snapshot：`00_System/Taxonomy_v2_Mapping.md` §2（defined 93 / used 41 / unused 53；frontmatter 内一致口径）。
- Review：`02_Phase_0_1_Ontology_and_Universe.md` §3 扇区草案；`00_Master_Roadmap.md` §8 Pilot 建议。
- Affected object IDs：所有携带 v0.1 tag 的 v0.2 正式对象（41 个使用的 tag，主在 PRJ-001/PRJ-002 Event 与 Company）。
- Test or validation output：`research-os validate` 0 errors / 0 warnings；本 RCP 不改对象，不影响 validation。

## Proposed change

1. **Taxonomy v2 生效**：以 `Taxonomy_v2_Proposal.md` 为内容，13 个 L1 扇区作 **Sector 实体（SEG-ID，依 D6）**，5 个横向维度扩展前缀（REG/SUP/CAP/CYC/RGT）。
2. **v1→v2 映射表权威化**：`Taxonomy_v2_Mapping.md` 作为权威映射；keep/map/deprecate 决定生效。
3. **边界项决定**（reviewer：max，2026-08-05）：
   - R1：历史对象 tag **不回填，保留旧 tag**；mapping 表提供语义映射；补 SEG 关系时人工逐批核。
   - R2：`APP-CODING` **keep 为 tag**，归 Enterprise Applications 下 "AI Developer Tooling" 子域。
   - R3：`MOD-*` 6 个 **全 map 到 Models 扇区下 Technology 实体**。
   - R4：`INF-CLOUD-AI` **归 Sector=Cloud & AI Infrastructure**；边界 = 云端模型平台/推理服务；与 Models、Data & AI Development 不重叠。
   - R5：INF 父类聚合 tag（INF-COMPUTE/MEMORY/NETWORK/DATACENTER）**deprecate**，历史沿用 R1 不回填。
   - R6：`SRV-DATA-LABELING` 默认归 Services，RCP 批准时现场定；若与 Data & AI Development 重叠明显再调。
4. **兼容窗口**：退役产业 tag 在至少一个版本周期保留 mapping 兼容（Phase 0-1 §11）。
5. **本 RCP 不创建任何 Sector/Technology/Product 实体**——实体创建与 Schema 落地属 RCP-v03-003 + WP-102。

## Alternatives considered

- **全 keep v0.1**：保留 53 个未用 tag 与扁平结构 → 无法支撑 v0.3 跨板块影响分析与 Pilot 价值链。
- **自动回填历史对象 tag 为 SEG 关系**：违反 Taxonomy §5"改变历史对象使用的标签需人工审核"，且易引入语义漂移。
- **MOD-* 全 keep 为 tag**：与 INF-* 不一致且模型类型更适合用 Technology 实体表达；R3 已选 map。
- **暂不加任何横向维度前缀**：v0.2 实际已需要地区/监管/周期维度，推迟会让 Pilot 数据缺失维度。

## Risks

- 退役 tag 后引用旧 tag 的下游（Event/Report）可能找不到新表达 → 缓解：mapping 表 + 兼容窗口；历史对象不删除旧 tag（R1）。
- REG 与 RGT 前缀易混 → 缓解：Taxonomy 文档明确备注区分；可在 Schema parser 加校验。
- 13 个 L1 扇区与 PRJ-002 主题未必一一对齐 → 缓解：Pilot 选 AI Compute Chain（D3）恰覆盖多扇区，作为首次映射验证。
- 与 RCP-v03-003 永久 ID 体系需同步 → 缓解：本 RCP 只定 Taxonomy 语义，SEG-ID 命名细节由 RCP-v03-003 落地。

## Migration

- 批准后：Taxonomy.md 标注被 v2 取代（保留 v0.1 作为历史参考），Taxonomy_v2_Proposal 转 authoritative。
- 历史对象：不回填（R1）；保留旧 tag。
- 新对象：v0.3 起用 SEG-ID + Technology/Product 实体表达产业归属，横向维度用 keep 的与新增的 tag。
- migration/rollback 由 WP-123 落实，本 RCP 不执行。

## Acceptance tests

- RCP-v03-002 批准后：Taxonomy v2 与映射表成为权威；后续 WP-101 Schema proposal 须与 Taxonomy v2 一致（Phase 0-1 §9 Gate）。
- 不自动改写任何 v0.2 对象 tag（R1 守住）。
- `research-os validate` 仍 0 error（本 RCP 不增减对象）。
- 与 `Metadata_Schema_v0.3_Proposal`（A-005/WP-101）的 Sector 实体 Schema 一致（核对留到 WP-101 提案阶段）。

## Human decision

- Decision：批准（accept RCP-v03-002 as drafted，含边界项 R1–R5）
- Reviewer：max
- Date：2026-08-05
- Reason：研究者在交接 A-002/A-002 边界项后批准 Taxonomy v2 与稳定板块 ID 体系。
  13 个 L1 扇区作为 Sector 实体（SEG-ID，依 D6）、5 个横向维度扩展前缀
  （REG/SUP/CAP/CYC/RGT）、v1→v2 权威映射表、以及 R1–R5 边界决定整体接受。

## Implementation record

- Changed files：本文件（proposed → approved）；`Taxonomy_v2_Proposal.md` 状态转
  authoritative；`Taxonomy.md`（v0.1）标注被 v2 取代并保留为历史参考；
  `Taxonomy_v2_Mapping.md` 作为权威映射。
- Test result：not run（本 RCP 为治理边界批准，无代码/对象变更）
- Validation result：`research-os validate` 0 errors / 0 warnings（批准前后一致）
- Effective date：2026-08-05（批准即生效）