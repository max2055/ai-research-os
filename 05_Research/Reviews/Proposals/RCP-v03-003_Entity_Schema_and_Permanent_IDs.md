# Rule Change Proposal RCP-v03-003

Proposal ID：RCP-v03-003

状态：proposed（草案由 Agent 整理，人工批准前不生效）

创建日期：2026-08-05

提议人：max（草稿由 Agent 按 v0.3 规划整理）

## Target

受影响的规则、Schema、永久 ID、Agent 边界：

- 新增正式对象类型与永久 ID 体系（`Metadata_Schema.md` v0.2 → v0.3）
- `02_Phase_0_1_Ontology_and_Universe.md` §4 Entity Schema 草案落为正式 Schema
- `00_System/Metadata_Schema_v0.3_Proposal.md`（A-005）转为 authoritative
- `00_System/ID_Conflict_Analysis.md`（A-006） parser 歧义处理方案认定
- `00_System/Migration_Guide_v0.3.md`（A-007）migration 顺序认定
- Agent 边界：不变（Agent 可提议实体草稿，不自动批准；新建 entity 仍需人工 Review Decision）

## Observed problem

只记录可引用的失败、warning、返工或研究质量问题：

- v0.2 Schema 只有 9 个对象类型（Source/Event/Thesis/Company/Report/Project/Review/Action/Job），无法承载 v0.3 的 Sector/Technology/Product/Security/Metric 等正式实体，跨板块影响分析、Universe 映射与 Candidate 提升都无法落地。
- v0.2 Company 与可交易证券耦合，无法处理多上市地、ADR、私有公司与证券变更（Phase 0-1 §4.3）。
- v0.1 用扁平 tag 表达产业细分（INF-GPU/APP-CRM），但 Taxonomy v2（RCP-v03-002 approved）已将产业归属迁到 Sector 实体；没有 Sector Schema 就无法引用扇区。
- 指标定义（Metric）缺少独立对象，财年/口径/观测值无统一口径层（Phase 0-1 §4.5）。
- 新 14 个前缀无 Schema 注册，validator/index/repository 无法识别新对象。

## Evidence

- Metrics snapshot：A-001/002/003 审计（v0.2 对象 166、0 error）+ A-006 ID 冲突分析（v0.2 实际前缀 SRC/EVT/REV/ACT/COM/THS/PRJ/RPT/JOB，新 14 前缀零冲突）
- Review：`02_Phase_0_1_Ontology_and_Universe.md` §4 Entity Schema 草案、§9 测试要求、§11 回滚
- Affected object IDs：所有 v0.2 Company（8 个 COM-*）需无损读取；新 Schema 当前无既有对象（仅 placeholder）
- Test or validation output：`research-os validate` 0 errors / 0 warnings；本 RCP 不创建对象，不影响 validation

## Proposed change

1. **5 个 Phase 0-1 范围实体 Schema 确认**：Sector / Security / Product / Technology / Metric Definition（A-005 §3/§5/§6/§7）。其余 9 个对象类型（CHN/REL/IMP/MOD-ANL/ANL/FCT/RES/VAL/REC）ID 占位，详细字段留后续 RCP（004/006/007/008/009）。
2. **schema_version=2 启用**：新实体用 `schema_version: 2`；v0.2 对象（含现存 8 个 Company）保持 `schema_version: 1` 不强制升级；v0.3 reader 须**无损读取 v0.2 对象**（compat 测试强约束，Phase 0-1 §9 Gate）。
3. **Company v0.3 扩展（optional，不回填）**：`legal_name / company_stage / headquarters / region_primary / sector_ids / product_ids / technology_ids / security_ids / coverage_tier / source_channel_ids / key_metric_ids`；全部 optional + 默认值；**不自动回填**（R1）；人工升级走 `--apply` 与逐对象审。
4. **14 个新永久 ID 认定 + parser 歧义处理**（A-006 §5 D1–D7）：
   - `MOD-ANL-` 双段前缀：parser 锚定 `^MOD-ANL-`，不复用单段 `MOD-`
   - `INS-<market>-<ticker>`：market 定长 `[A-Z]{2,6}`，ticker 允许连字符
   - `MET-`：唯一表 Metric Definition（v0.2 无 `MET-` 对象）
   - `ANL-`(Run) vs `MOD-ANL-`(Mode)：parser 按前缀严格分派
   - 日期型 ID 只从 `id:` 行读，不全文匹配
   - slug 限 `[a-z0-9-]`，不允许连字符以外的特殊字符
5. **Region 优先级落地**（D-REGION-SCOPE）：Company `region_primary` 承载主地区（`REG-cn`/`REG-us`/`REG-<region>`）；Sector `core_company_ids` 按中美优先选用——非中美企业进 Core 须写理由。`REG-` 前缀已由 RCP-v03-002 批准，本 RCP 不改 Taxonomy。
6. **Migration 顺序认定**（A-007）：MIG-v0.3-001 注册 Schema → WP-102 实现 Pydantic+validator+parser+测试 → MIG-v0.3-002 Company 可选字段（dry-run→apply，人工逐点）→ WP-120 MIG-v0.3-003 Sector 入驻（人工批席位）→ validate/index/test/recovery 演练。MIG-v0.3-004（Taxonomy v0.1 标注 superseded）已在 RCP-v03-002 批准时完成（commit `44ff0aa`）。
7. **回滚与兼容**（Phase 0-1 §11 + R1）：独立 migration；Git baseline + 对象 hash manifest；历史 tag 不回填（R1）；旧 Tag 映射保留至少一个版本周期；退役用 `retired_at`/`superseded_by` 不删 ID；派生 index 可直接重建而回滚。

## Alternatives considered

- **不动 v0.2 Company**：Sector/Product 等引用不到所属实体，影响分析与 Universe 无法落地（不可行）。
- **强制升级现存 8 个 Company 到 schema_version=2 + 自动回填**：违反 R1 与 Taxonomy §5"改变历史对象使用的标签需人工审核"（不可行）。
- **Company 与 Security 继续耦合**：无法处理 ADR/多上市地/证券变更（Phase 0-1 §4.3 明确要求分离）。
- **一次性定义全部 14 对象类型的 Schema**：超出 Phase 0-1 范围，与后续 RCP-006/007/008/009 越界（不在本 RCP 范围）。
- **`MOD-` 单段前缀复用为 Model 对象**：与 `MOD-ANL-` 双段易歧义；本 RCP 禁用单段 `MOD-` 作 Model，Model 类型若引入另起新前缀。

## Risks

- v0.2 Company 无损读取破损 → 缓解：compat round-trip 测试 + 8 个现存 COM-* 全部纳入 WP-102 测试矩阵（Phase 0-1 §9）。
- `INS-<market>-<ticker>` 连字符切分歧义 → 缓解：market 定长 + parser 单测（D2）。
- `MOD-ANL-` 与未来 `MOD-` 误派 → 缓解：parser 锚定双段前缀 + 禁用单段 `MOD-`（D1）。
- 13 个 Sector 实体入驻时席位选用争议（地区优先级）→ 缓解：WP-120 人工批席位 + 理由入字段；D10 复核。
- migration 中途失败留半状态 → 缓解：dry-run 优先 + 原子 apply + hash manifest 回滚（A-007 §6）。

## Migration

- 见 A-007 `Migration_Guide_v0.3.md`：MIG-v0.3-001/002/003，部署顺序 §4。本 RCP 只认定顺序与约束；执行属 WP-102/120 / RCP 批准后。

## Acceptance tests

- RCP-v03-003 批准后：A-005 转 authoritative；A-006 parser 方案、A-007 migration 顺序生效。
- WP-102 实现须含：5 个新 Schema 单测、v0.2 Company round-trip、ID parser（含 D1–D7 歧义）、index/register 接入、migration dry-run/apply/rollback。
- 全仓库 `validate` 仍 0 error；`index --check` 无新增 drift；pytest 覆盖率不低于 80% Gate。
- 不创建任何实体（实体创建属后续 WP-120，需 RCP-v03-003 批准 + 人工席位审）。
- 历史对象 tag 不回填（R1）；不覆盖永久 ID；不删 v0.1 tag。

## Human decision

本 RCP 集中以下人审点（每项 default 已在 Evidence/Proposed change 标注，待 max 批准或修改）：

1. 启用 `schema_version=2`（v0.2 保持 1，无损读取）
2. 5 个 Phase 0-1 实体 Schema 字段确认（Sector/Security/Product/Technology/Metric）
3. Company v0.3 扩展 optional + 不回填（R1）
4. 14 新前缀认定 + parser 歧义处理 D1–D7
5. Company 与 Security 分离 (`security_ids` 引用)
6. Migration 顺序 MIG-001→002→003
7. 禁用单段 `MOD-` 作 Model（防与 `MOD-ANL-` 歧义）

- Decision：（待 max 批准生效）
- Reviewer：（待填，建议 max）
- Date：（待填）
- Reason：（待填）

## Implementation record

- Changed files：批准后记录（A-005 转 authoritative、A-006/A-007 方案生效、WP-102 起落地）
- Test result：批准后由 WP-102 实现并运行
- Validation result：`research-os validate` 0 errors（批准前后一致，因无对象变更）
- Effective date：批准后记录（MIG-v0.3-001 注册 Schema 起按 WP-102 落地）