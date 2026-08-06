# Rule Change Proposal RCP-v03-004

Proposal ID：RCP-v03-004

状态：approved（2026-08-06，reviewer：max）

创建日期：2026-08-06

提议人：max（草稿由 Agent 按 v0.3 规划整理）

## Target

受影响的规则、Schema、永久 ID、Agent 边界：

- Phase 2（`03_Phase_2_Intelligence_Ingestion.md`）引入 Candidate Operational
  Store（SQLite）
- `00_Master_Roadmap.md` §9 关键人工决策点：Candidate store 事实边界
- 新增 Candidate operational 数据（非正式对象）：candidates / candidate_events /
  runs 表
- Agent 边界：Candidate 数据由 Agent 可写（operational store），但**提升为正式
  Source 必须经人工 Review**；Agent 不得把 Candidate 当作权威事实源

## Observed problem

只记录可引用的失败、warning、返工或研究质量问题：

- 当前所有采集（SEC、官方 IR、TrendForce 等）均为**手动**：每个 WP 手工抓取、
  手工建 Source/Event。无法规模化支撑"每日情报发现"目标。
- 无 Candidate 暂存层：候选新闻若直接写成正式 Source，会污染事实源边界（候选
  未审、来源未核验、重复未去重）。
- v0.2/v0.3 阶段 1 的 evidence 覆盖低（source 39%）：59 家 Core 中仅 23 家有
  reviewed Event 点名，其余 36 家缺证据——需规模化采集补足，而手动采集不可持续。
- 无去重/聚类/评分机制：同一公告被多来源转载时无法识别重复，无法按相关性和
  新颖性排序候选。

## Evidence

- Metrics snapshot：`METRICS-20260806.json`（source coverage 39%，23/59）
- Review：`03_Phase_2_Intelligence_Ingestion.md` §3/§4（Channel + Candidate
  schema 草案）、§12（14 天真实 Gate）
- Affected object IDs：无既有正式对象受影响；新增 operational store 数据
- Test or validation output：`research-os validate` 0 errors / 0 warnings；
  本 RCP 不创建正式对象，不影响 validation

## Proposed change

1. **Candidate Operational Store（SQLite）**：`candidates`、`candidate_events`、
   `runs` 三表（Phase 2 §4 草案）作为**可重建的 operational store**，非权威事实源。
   - 事实源仍为 reviewed Markdown Source/Event；SQLite 可删除重建。
2. **事实边界（D5 决策落点）**：Candidate 数据不得自动成为 reviewed Evidence；
   提升路径 = Candidate → Source capture dry-run → Source apply + 人工 Review
   Decision（Phase 2 §8）。
3. **Retention**：按 Channel `retention_days` 清理过期 Candidate；dismissed/
   expired Candidate 不永久保留；promoted 的 Candidate 永久链接到 Source。
4. **重建与备份**：Candidate DB 为派生数据，随 Recovery_Runbook 策略备份；可
   从 Channel 重跑重建。
5. **迁移**：新增 operational migration（`B-004 Candidate migration engine`），
   dry-run → apply → rollback；不迁移既有正式对象。

## Impact and risks

- 数据量：Candidate 远大于正式对象；需明确 retention 与清理策略，避免无限增长。
- 许可边界：采集须遵守 robots/许可/频率（细化于 RCP-v03-005）。
- 不引入分布式队列：单机 scheduler 足够时保持简单（Phase 2 §10）。

## 不做的事

- 不自动批准 Source/Event。
- 不自动改变 Thesis confidence。
- 不把 Candidate SQLite 当权威事实源。
- 不默认下载候选链接的所有子链接。
- 不用 LLM 摘要替代原始 Source。

## Review points（reviewer：max，2026-08-06，全部采纳默认）

1. ✅ Candidate retention 默认值：保留 30 天；dismissed/expired 即清；promoted 永留
   （永久链接到 Source）
2. ✅ 三表结构（candidates / candidate_events / runs）符合 Phase 2 §4 草案
3. ✅ Agent 可写 Candidate 但不可自动提升（promote 须人工 Review Decision）
4. ✅ B-004 migration engine 不独立 RCP，并入本 RCP 实施（operational 表
   schema 升级/回滚走 B-004，不引入正式对象）

- Decision：批准（accept RCP-v03-004 as drafted，4 项人审点全部采纳默认）
- Reviewer：max
- Date：2026-08-06
- Reason：与 Phase 2 §4/§8 草案、D5 决策（Candidate store 用 SQLite）一致；
  事实边界（Candidate 非权威源、promote 须人审）符合 v0.3 治理。

## Implementation record

- Changed files：本文件（proposed → approved）；生效后由 WP-200 起落地 Candidate
  DB ADR（B-003）+ migration engine（B-004）+ Candidate schema
- Test result：not run（本 RCP 为治理边界批准，无代码变更；测试在 WP-200 落地后运行）
- Validation result：`research-os validate` 0 errors / 0 warnings（批准前后一致，
  因无对象变更）
- Effective date：2026-08-06（批准即生效；WP-200 起实施）

## 参考

- `03_Phase_2_Intelligence_Ingestion.md`
- `00_Master_Roadmap.md` §9（D5：Candidate store 使用 SQLite）
