# 关系数据 WP Handoff — Pilot 价值链 Ontology Assertion（REL-*）

Handoff ID：HOF-20260805-REL
日期：2026-08-05
发送人：Claude（Agent）
接收人：max（研究者）
Project ID：PRJ-001 / PRJ-002（Universe 为跨项目基元）

## Scope

按 `08_Agent_Execution_Protocol` 工作包输入合同，关系数据 WP 范围 = 为 51 家
Pilot Core Company（9 Sector）建首批价值链关系 Ontology Assertion。
机制（Schema/校验/导出）已由 WP-103 完成；本 WP 是数据落地。

范围决定（reviewer：max，2026-08-05）：
- **先建 pending 关系**：全部 `review_status: pending`（不 approve）——validate
  保持 0 error
- **证据后审**：30 条人审子 Gate 推迟到 Compute Chain 证据 WP 之后
- 关系是价值链知识草案，方向/范围待 max 抽查

## Rules and templates read

- `AGENTS.md`、`README.md`、`00_System/Research_Rules.md`、`Source_Policy.md`
- `00_System/v0.3_.../02_Phase_0_1_...md`（§5 Ontology Assertion、§7 A-017）、
  `08_Agent_Execution_Protocol.md`
- `07_Templates/Research_Handoff.md`

## Objects created or changed

| Object | Action | Path | Review status |
|---|---|---|---|
| 253 × Ontology Assertion（REL-*） | 新增 | `05_Research/Assertions/` | **pending** |
| `new-assertion` CLI | 新增 | `src/research_os/cli.py` | — |
| `prepare/render_assertion_draft` | 新增 | `src/research_os/services/drafts.py` | — |
| `next_object_id` 扩展 | 修改 | drafts.py（+ontology_assertion） | — |
| OBJECT_PATTERNS | 扩展 | `repositories/markdown.py`（+Assertions/） | — |
| runtime 导出 | 修改 | `runtime/product.py` | — |
| 测试计数断言 | 更新 | `09_Automation/tests/test_schemas.py`（+ontology_assertion 253） | — |
| 文档 | 更新 | `Known_Limitations_v0.2.md` | — |

## Sources used

- WP-103 机制（OntologyAssertionSchema/validate_refs/export）
- Phase 0-1 §5（关系约束）、RCP-v03-003（实体 Schema）

## Facts established

- **253 条 assertion**（全部 pending）：
  - SUPPLIES 186（环1→2、2→3、3→5、4→3/5、5→7、6→7、7→8）
  - COMPETES_WITH 32（同环竞争；导出层对称派生 64 边）
  - DEPENDS_ON 8（芯片依赖制造/存储）
  - ENABLES 18（设备→制程、云→模型）
  - PARTNERS_WITH 4、PRODUCES 2、OWNS 1
- 导出：488 节点、1291 边（含对称派生）
- validate 0 error（pending 无证据不报错）；index 无 drift；119 tests 全绿

## Inferences proposed

- 关系方向为 Agent 基于价值链知识草案（TSMC SUPPLIES NVIDIA、NVIDIA COMPETES_WITH
  AMD 等）——**待 max 抽查**，尤其 COMPETES_WITH 边界与非中美节点关系
- 数量超计划（120-150 → 253）：SUPPLIES 采用全连接（每上游供所有下游）导致

## Conflicts and unknowns

- 无冲突。validate 0 error；index 无 drift。
- **证据缺失**：所有 assertion 无 Evidence——30 条人审子 Gate 推迟到证据 WP
- 2 条 OWNS 关系（COM-alibaba/COM-bytedance 母体）因母体不在 Universe 未建

## Human decisions required

- **关系抽查**：253 条 pending 关系方向/范围是否接受（尤其 COMPETES_WITH、非中美
  节点）——不批准即保持 pending，批准需等证据 WP 后 approve
- 30 条人审子 Gate 排期待定（依赖 Compute Chain 证据 WP）

## Verification

- Validate：0 errors / 0 warnings（对象 488 = 234 原 + 253 assertion + 1 个 HOME？——实际 488 节点含 assertion 边）
- Index check：global + PRJ-001 + PRJ-002 全 PASS
- Tests：119 passed（计数断言更新）
- Coverage：83%（≥80 Gate）；ruff / mypy strict：pass
- Export：`research-os export --format jsonl --apply` 见 287 关系边 + 对称派生

## Recommended next action

- **Compute Chain 证据 WP**（Source/Event 采集 + 人审）：为关系提供 reviewed
  Evidence → 253 条 assertion 可 approve（30 条人审子 Gate 完成）
- 或 WP-122（Universe coverage 指标 + 真实抽检）
- 或先暂停，max 抽查 253 条关系草案
