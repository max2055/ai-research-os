# WP-120 Handoff — Pilot Core Universe（Sector + Company 实体）

Handoff ID：HOF-20260805-WP120
日期：2026-08-05
发送人：Claude（Agent）
接收人：max（研究者）
Project ID：PRJ-001 / PRJ-002（Universe 为跨项目基元，project_ids=[]）

## Scope

按 `08_Agent_Execution_Protocol` 工作包输入合同，WP-120 范围 = Pilot Core
Universe 建设：9 个 L1 Sector + 51 家 Pilot Core Company + v0.2 8 家补 v0.3
扩展字段 + 实体创建管道（new-entity CLI / OBJECT_PATTERNS / ID_PATTERNS）。
名单由 max 逐环节拍板（2026-08-05）。

## Rules and templates read

- `AGENTS.md`、`README.md`、`00_System/Research_Rules.md`、`Source_Policy.md`、
  `Metadata_Schema.md`（v0.2）、`Metadata_Schema_v0.3_Proposal.md`（A-005）
- `00_System/v0.3_.../00_Master_Roadmap.md`、`02_Phase_0_1_...md`（§6 Universe
  选择 + §6.1 地区优先级）、`08_Agent_Execution_Protocol.md`
- `07_Templates/Research_Handoff.md`、`07_Templates/Company_Profile.md`

## Objects created or changed

| Object | Action | Path | Review status |
|---|---|---|---|
| 9 × Sector（SEG-*） | 新增 | `02_Knowledge/Sectors/` | **pending** |
| 51 × Company（COM-*） | 新增 | `02_Knowledge/Companies/` | **pending** |
| 8 × v0.2 Company | 补 v0.3 字段 | `02_Knowledge/Companies/` | reviewed（字段新增，旧 tag 未动） |
| 索引 5 个 | 重生成 | `08_Indexes/`、`05_Research/` | — |
| 代码 5 文件 | 新增/修改 | markdown.py / drafts.py / runtime / cli.py / policies.py | — |

## Sources used

- 名单：max 逐环节拍板（AskUserQuestion，2026-08-05）
- Taxonomy v2（RCP-v03-002）、Entity Schema（RCP-v03-003）
- 地区约束（D-REGION-SCOPE）

## Facts established

- **9 Sector**：Compute Chain 8 环节 + enterprise-applications，各含
  `core_company_ids`（中美优先 + 非中美关键节点）
- **51 家 Pilot Core Company**，全部 `schema_version=2`、`review_status: pending`
- **v0.2 8 家补字段**：`sector_ids`/`region_primary`/`coverage_tier`，旧 tag 未动（R1）
- 对象总数 **166 → 225**（10 类型）
- `new-entity` CLI 支持 sector/company 的 dry-run → `--apply`
- `ID_PATTERNS` 补齐 5 个 v0.3 类型（WP-102 遗漏，本 WP 修复）

## Inferences proposed

- 非中美关键节点（ASML/TSMC/SK hynix/Samsung/TEL/信越/ASE）以 `region_primary`
  非 REG-us/cn 标记，理由写入 company body——符合 D-REGION-SCOPE"关键卡位理由"
- v0.2 8 家：微软/OpenAI/Anthropic 归 core（环节 7/8），其余 5 家归 tracked
  （enterprise-applications）

## Conflicts and unknowns

- 无冲突。111 tests 全过；validate 0 error；index 无 drift。
- Unknown：实体尚未人工 review（pending）；`coverage_tier` 的 tracked 归属
  （Oracle 等）是 Agent 建议，未逐家人工核。

## Human decisions required

- **实体人审**：51 家新 Company + 9 个 Sector 均 `review_status: pending`，需
  max 通过 `review apply` 逐家/逐批人工审核转 reviewed（不自动批准）。
- 席位归属（尤其 tracked 5 家）如与你的判断不同，指出即改。

## Verification

- Validate：0 errors / 0 warnings（225 对象 / 10 类型）
- Index check：global + PRJ-001 + PRJ-002 全 PASS，0 drift
- Tests：111 passed（company 8→59、sector 9 计数断言已同步）
- Coverage：84%（≥80 Gate）；ruff / mypy strict：pass
- R1：v0.2 旧 tag 零改动；新实体全 pending

## Recommended next action

- **实体人审**（`review apply` 批量审核 51 家 + 9 个 Sector）→ 转 reviewed 后
  Universe 才有权威引用基础
- 或 WP-103（Ontology Assertion + 引用完整性校验——实体已存在，可启动）
- 或 WP-122（coverage 指标 + 真实抽检）
