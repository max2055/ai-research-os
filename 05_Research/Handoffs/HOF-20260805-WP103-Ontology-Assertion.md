# WP-103 Handoff — Ontology Assertion + 引用完整性校验

Handoff ID：HOF-20260805-WP103
日期：2026-08-05
发送人：Claude（Agent）
接收人：max（研究者）
Project ID：PRJ-001 / PRJ-002（机制层共享）

## Scope

按 `08_Agent_Execution_Protocol` 工作包输入合同，WP-103 范围 = Phase 0-1
A-011/A-012：Ontology Assertion（REL-*）Schema + 注册 + 引用完整性校验 +
ontology export 扩展。**机制先行，数据后置**（max 决策 2026-08-05）——不建
REL-* 数据，Phase 0-1 Gate 的 100+ 条 + 30 人审留独立后续 WP。

## Rules and templates read

- `AGENTS.md`、`README.md`、`00_System/Research_Rules.md`、`Source_Policy.md`、
  `Metadata_Schema_v0.3_Proposal.md`（A-005）
- `00_System/v0.3_.../02_Phase_0_1_...md`（§5 Ontology Assertion 草案）、
  `08_Agent_Execution_Protocol.md`
- `07_Templates/Research_Handoff.md`

## Objects created or changed

| Object | Action | Path | Review status |
|---|---|---|---|
| OntologyAssertionSchema | 新增代码 | `src/research_os/schemas/ontology_assertion.py` | — |
| registry SCHEMAS | 扩展 | `registry.py`（+ontology_assertion） | — |
| ID_PATTERNS | 扩展 | `domain/policies.py`（+REL- 正则） | — |
| ONTOLOGY_PREDICATES / SYMMETRIC_PREDICATES | 新增常量 | `domain/policies.py` | — |
| validate_refs | 扩展 | `services/validation.py`（v0.3 实体引用 + 断言证据） | — |
| ontology_graph | 扩展 | `services/ontology.py`（REL-* 节点/边 + 对称派生） | — |
| 测试 | 新增 8 项 | `09_Automation/tests/test_schemas.py` | — |
| 文档 | 更新 | `Known_Limitations_v0.2.md` | — |

无新对象创建（机制先行）；对象数仍 234。

## Sources used

- Phase 0-1 §5（Ontology Assertion 草案）、RCP-v03-003（实体 Schema）、
  WP-102（schema 注册基础）

## Facts established

- Ontology Assertion Schema：REL-YYYYMMDD-NNN、12 predicates、schema_version=2
- `validate_refs` 现校验：company→sector/product/technology/security/metric 引用、
  sector→company（core/tracked）、security→company、product/technology→company/sector、
  assertion→subject/object/evidence/source
- reviewed assertion 强制 >=1 reviewed Evidence（REF003/REF004）
- ontology export 含 REL-* 断言节点 + 边；对称 predicate（COMPETES_WITH 等 4 个）
  由导出层确定性派生反向边
- 119 tests 全过（111 + 8 新增）；validate 0 error；coverage 84%

## Inferences proposed

- 对称关系由导出层派生而非写库（Phase 0-1 §5："对称关系只能由 service 生成
  确定性反向派生，不复制权威对象"）
- `expect_refs`/`expect_ref` 的 `expected_type` 允许 None（仅存在性校验）——
  owner_entity_ids/subject_id/object_id 是多类型引用

## Conflicts and unknowns

- 无冲突。119 tests 全过；validate 0 error；index 无 drift。
- Unknown：无 REL-* 数据（数据后置），导出中 assertion 边为 0——机制已就绪，
  待数据 WP 填充。

## Human decisions required

- 无（机制层；数据 WP 需另行人审）。

## Verification

- Validate：0 errors / 0 warnings
- Index check：global + PRJ-001 + PRJ-002 全 PASS
- Tests：119 passed（+8 新增）
- Coverage：84%（≥80 Gate）；ruff / mypy strict：pass
- 引用完整性：现有 234 对象全部通过新校验（sector_ids 等指向存在实体）

## Recommended next action

- **关系数据 WP**（A-017/独立 WP）：建首批 100+ REL-* assertion（Pilot 价值链
  SUPPLIES/DEPENDS_ON/COMPETES_WITH 等）+ 30 条人审 → Phase 0-1 Gate
- 或 WP-122（Universe coverage 指标 + 真实抽检）
- 或 WP-121（按关系类型分包建关系）
