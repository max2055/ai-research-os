# Rule Change Proposal RCP-v03-001

Proposal ID：RCP-v03-001

状态：proposed

创建日期：2026-08-05

提议人：max（草稿由 Agent 按 v0.3 规划整理，人工批准前不生效）

## Target

受影响的规则、Schema、Taxonomy、Agent 边界或自动化：

- 产品定位：AI Research OS v0.2 Evidence Kernel → AI Industry Intelligence & Decision OS
- `00_System/Source_Policy.md`（v0.2）：Candidate 与 Source 的权威边界
- `00_System/Metadata_Schema.md`：新增正式对象类型与永久 ID
- `00_System/Research_Rules.md` / 根目录 `AGENTS.md`：审核边界与 Agent 权限
- v0.3 `01_Product_Charter_and_Governance.md`：权威分层与投资/研究边界
- v0.3 `00_Master_Roadmap.md` 阶段 0 Gate

## Observed problem

只记录可以引用的失败、warning、返工或研究质量问题：

- v0.2 产品边界是单一专题（企业软件价值链）研究；若不重定义，无法承载 AI 全产业链 Universe、每日候选情报、跨板块 Ontology、影响分析、Forecast/Recommendation。
- 若不在编码前明确 Candidate/Source 边界，高频采集的候选记录会被误当正式 Source，破坏“Markdown 为唯一权威事实源”原则。
- 新对象类型（Sector、Technology、Product、Security、Metric、Source Channel、Ontology/Impact Assertion、Analysis Mode/Run、Forecast、Valuation、Recommendation）目前没有 Schema 或永久 ID 归属。
- 若不定义投资边界，系统可能从“技术领先”直接推论买卖方向（违反 Research_Rules §6 技术与投资隔离）。

## Evidence

- Metrics snapshot：`00_System/v0.3_AI_Industry_Intelligence_OS/WP-000_Baseline_Audit.md`（166 对象、0 error、98 tests、84.28%）
- Review：`00_System/v0.3_AI_Industry_Intelligence_OS/00_Master_Roadmap.md` §9 关键人工决策点；`01_Product_Charter_and_Governance.md` §3 权威分层、§4 Candidate/Source 边界、§6 投资边界、§7 新对象 ID、§8 RCP 清单、§10 Gate
- Affected object IDs：现有 SRC-*/EVT-*/THS-*/COM-*/RPT-*/REV-*/ACT-*；新增 SEG/SEC、TEC、PRD、INS、MET、CHN、REL、IMP、MOD-ANL、ANL、FCT、RES、VAL、REC
- Test or validation output：`research-os validate` 0 error / 0 warning；index PRJ-002 1 drift（与本次 RCP 无直接关系，独立小任务处理）

## Proposed change

1. **产品重定义**：在 v0.2 Evidence Kernel 之上建设 AI Industry Intelligence & Decision OS；目标闭环见 00_Master_Roadmap §1。保留 v0.2 全部继承原则。
2. **Candidate 与 Source 权威边界**：
   - Candidate 是低成本、高吞吐的发现记录（建议 SQLite operational store），允许标题/摘要/URL/日期/Channel/hash/去重簇/entity proposal/评分/抓取状态/保留策略。
   - Candidate **不得**：被 Report 当作事实引用；自动提升 Source grade；自动支持或反对 Thesis；自动生成 Recommendation；无正文时伪装成已归档 Source。
   - 正式 Source 继续满足 Source_Policy.md；Candidate 提升为 Source 必须经人工确认，并保留永久关联。
3. **权威分层**：Candidate/Source/Event/Stable entity/Ontology edge/Impact Assertion/Analysis Run/Thesis/Forecast/Valuation/Recommendation Draft/Resolution 默认 `pending`，仅 `reviewed` 可被权威引用（详见 Charter §3 表格）。
4. **投资与研究边界**：不自动下单、不按模型置信度自动计算仓位、不把技术领先等同股东回报、无价格/证券身份/估值依据时不出买卖方向、不把未解析 Forecast 计为成功、不用后见之明修改原 Forecast。
5. **新增正式对象与永久 ID（proposal）**：SEG(Sector)/TEC/PRD/INS/MET/CHN/REL/IMP/MOD-ANL/ANL/FCT/RES/VAL/REC。`SEG` vs `SEC` 前缀待阶段 0 人工决策（避免与美国 SEC Adapter 混淆，倾向 SEG）。
6. **后续 RCP 排期**：RCP-v03-002~010 在对应 Phase 开始前批准（见 Charter §8）。

## Alternatives considered

- 不重定义产品，继续扩充企业软件专题 → 无法覆盖 AI 全产业链需求。
- 所有候选直接写入正式 Source → 破坏事实源治理，数据量与噪声不可控。
- 引入图数据库作为权威事实源 → 在关系类型稳定前过早（违反非目标）。

## Risks

- Candidate store 越界成为事实源 → 缓解：只读边界 + validation 拒绝非权威引用。
- 新 ID 前缀冲突或解析歧义 → 缓解：永久 ID 唯一性/parser 检查（RCP-v03-003 落实）。
- 投资结论过度 → 缓解：Recommendation validator + 人工批准 Gate。
- 本 RCP 范围外移（如把 Schema 实现提前）→ 缓解：本 RCP 只批准边界，不批准 Schema/ID 实现。

## Migration

- 本 RCP 不改变现有 Schema，不迁移任何对象；仅批准产品定位与权威边界。
- 新 Schema/永久 ID 在 RCP-v03-003 批准后引入；v0.1 tag 在 RCP-v03-002（Taxonomy v2）中映射。
- 生效只需本文件获人工批准，无代码变更。

## Acceptance tests

- 批准后 v0.3 阶段 0 其余 Gate 可开，随后才可进入 Taxonomy/Schema 实施。
- Candidate 数据被 Report 引用时 validation 拒绝。
- 无自动 grade / Thesis confidence / Recommendation 状态修改。
- 未批准的新对象类型不得创建。

## Human decision

- Decision：（待填）
- Reviewer：（待填）
- Date：（待填）
- Reason：（待填）

## Implementation record

- Changed files：批准后记录
- Test result：批准后记录
- Validation result：批准后记录
- Effective date：批准后记录
