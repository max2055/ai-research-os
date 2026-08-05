# Migration Guide v0.3（A-007）

状态：`proposed / pending RCP-v03-003 approval`
创建日期：2026-08-05
工作包：WP-101 / A-007（migration 设计草案，不写 migration 代码）
依赖：`00_System/Migration_Guide_v0.2.md`、`02_Phase_0_1_Ontology_and_Universe.md` §11、`Taxonomy_v2_Mapping.md`（R1 不回填）、`Metadata_Schema_v0.3_Proposal.md`（A-005）
reviewer（待）：max（按 D9，Wave 1）

> 本文件是 v0.3 **migration 设计草案**，不是已执行的 migration。
> Schedule/ID/Schema 变更需 RCP-v03-003 批准；migration 执行属 WP-102/103。
> 本设计适用原则：v0.2 对象无损、可回滚、dry-run 优先、不覆盖 raw Source。

## 1. v0.3 迁移边界

v0.3 引入：
- 5 个新正式实体类型（Phase 0-1 范围）：Sector / Security / Product / Technology / Metric
- Company 扩展（v0.2 无损升级）
- 永久 ID 新前缀 14 个（A-006 确认无冲突）
- Taxonomy v2 扇区体系（RCP-v03-002 approved，但**历史 tag 不回填**）

后续 Phase（2/3/4/5/6）的 Candidate DB、Ontology Assertion、Analysis Mode、Forecast、Valuation、Recommendation 等各自的 migration 在对应 RCP 批准后单列，本文件不覆盖。

## 2. 设计原则（沿用 v0.2 + Phase 0-1 §11）

1. **v0.2 对象无损读取**：v0.2 Company（`schema_version=1`）在 v0.3 reader 下必须通过；
   新字段缺失走默认（空列表/None），不报错、不回填（compat 测试强约束）。
2. **历史 tag 不回填（R1）**：Taxonomy v1→v2 映射表语义保留，v0.2 对象的旧
   tag 不动；新 Sector `core_company_ids` 等通过新建实体引用，**不自动改写历史对象**。
3. **独立 migration**：新 Schema 在独立 migration 引入，与既有 migration 分号段。
4. **Git baseline + hash manifest**：migration 前记 Git commit 与对象 hash manifest。
5. **dry-run 优先**：所有写入 default dry-run，显式 `--apply`；apply 原子或可回滚。
6. **可回滚**：igration exclusive（删除新实体与 index）；旧 Tag 映射保留兼容窗口
   （Phase 0-1 §11）；不允许通过删除历史 tag 或 ID 完成回滚。
7. **crash/failure 不留半状态**（Agent Execution Protocol §6）。

## 3. Migration 列表

### MIG-v0.3-001：引入 schema_version=2 与新实体 Schema

- **范围**：注册 Sector/Security/Product/Technology/Metric 五个 Schema 到
  `src/research_os/schemas/` 与 `registry.py`；新增 Pydantic 模型与 ID parser（A-006 §5）。
- **不创建实体**：只注册 Schema；实体创建由 WP-120 手动 / 工具手动新建。
- **兼容**：v0.2 reader 继续接受 `schema_version=1`；v0.2 Company 不强制升级。
- **验证**：v0.2 全部 166 对象仍 validate 通过；98 测试不退化；新增"v0.2 Company
  round-trip"测试。
- **dry-run/apply**：`research-os migrate MIG-v0.3-001 --dry-run` 校验依赖；
  `--apply` 注册 Schema（多数是代码层，不改 Markdown）。
- **backup**：Git commit baseline + `02_Knowledge` 对象 hash manifest（按 v0.2 实践）。
- **rollback**：回退 registry 与 schema 文件到 v0.2；新 Schema 已创建的实体（若有）
  挂为 pending 但不删除——migration 只回退代码，不删数据。

### MIG-v0.3-002：Company 可选字段升级

- **范围**：为现有 8 个 Company 补 optional v0.3 字段槽（不强制、不回填）。
- **写入内容**：只补可为空的 schema_version=2 占位？**默认不自动升 schema_version**；
  Company 保持 v0.2 `schema_version=1` 直至人工升级；migration 工具可逐个流件升级
  但需 `--apply` 与人工批点。
- **不回填**（R1）：不自动给 Company 加 `sector_ids`/`region_primary` 等具体值——
  这些由后续 WP-120 人工补；migration 只确保 schema 接受新字段。
- **验证**：v0.2 Company round-trip；Company Schema v0.3 读取 v0.2 字段无错。
- **rollback**：恢复 frontmatter 到升级前 hash manifest。

### MIG-v0.3-003：Universe Sector 实体入驻（WP-120 触发，人工批）

- **范围**：创建首批 13 个 L1 Sector SEG-ID + 与 Taxonomy v2 对齐的子扇区。
- **触发**：属 WP-120（Pilot Universe），需 RCP-v03-003 批准 + 人工确认 SEG-slug 拼写
  与核心公司席位（按 D-REGION-SCOPE 优先中美）。
- **不回填**：不将历史对象 INF-* tag 自动转为 sector_ids；新对象引用新 Sector。
- **备份**：Git commit + 实体 hash manifest + Universe export snapshot。
- **rollback**：删除新建 Sector + 重建 index（派生 index 可直接重建，Phase 0-1 §11）。

### MIG-v0.3-004：Taxonomy.md 标注 superseded（已完成，非代码 migration）

- **范围**：`00_System/Taxonomy.md` 标注 superseded（RCP-v03-002 批准时已落），
  `Taxonomy_v2_Proposal` 转 authoritative。**无代码 migration**，仅治理文档迁移。
- 状态：**已完成**（commit `44ff0aa`）。

## 4. 部署顺序（Wave 1）

1. RCP-v03-003 批准 → MIG-v0.3-001（注册 Schema）。
2. WP-102 实现 Pydantic schemas + validator + ID parser + 测试。
3. MIG-v0.3-002（Company 可选字段，dry-run → apply，人工 Grimm 点审）。
4. WP-120：MIG-v0.3-003（Sector 入驻，人工批席位）。
5. validate/index/test/recovery 演练。

## 5. 验证 gate（每个 migration 完成）

- `research-os validate` 0 error / 0 warning
- `research-os index --check` global + per-project（PRJ-001/PRJ-002）无 drift
- pytest 覆盖率不低于当前 80% Gate
- ruff / mypy pass
- v0.2 对象 166 个数量与 hash manifest 一致
- 新实体 round-trip / ID parser / 兼容测试通过
- migration rollback 演练一次

## 6. 回滚与恢复

- 代码 migration（MIG-001）：回退 git commit；新 Schema 实体挂 pending 保留。
- 数据 migration（MIG-002/003）：从 hash manifest + Git 恢复；派生 index 重建。
- **不重用永久 ID**：退役用 `retired_at`/`superseded_by`，不删除历史。
- **旧 Tag 映射保留**至少一个版本周期（Phase 0-1 §11）。
- Clean-clone recovery 演练（v0.2 实践）：从 Git + 加密 Source 资产备份恢复。

## 7. 不做的事

- 不自动回填历史 Tag 为 sector_ids（R1）。
- 不自动为 Company 添加 `region_primary`/`sector_ids` 具体值（人工 WP-120）。
- 不迁移 Candidate（属 Phase 2 / RCP-v03-004）。
- 不迁移 Ontology/Impact/Analysis/Forecast/REC 字段（属后续 RCP）。
- 不删 v0.1 tag、不删历史 ID、不覆盖 raw Source。

## 8. 给 RCP-v03-003 的输入

- 本设计 + A-005 Schema + A-006 ID 冲突分析共同构成 RCP-v03-003 草案输入。
- RCP-v03-003 批准须包含：永久 ID 全集 confirmation、schema_version=2 启用、
  5 个 Phase 0-1 实体 Schema 字段 confirmation、migration 顺序 confirmation。
- WP-102 起按本设计落地。