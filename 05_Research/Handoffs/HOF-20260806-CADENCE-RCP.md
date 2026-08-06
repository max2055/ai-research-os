# v0.2 Cadence 启动 + Phase 2 RCP 起草 Handoff

Handoff ID：HOF-20260806-CADENCE-RCP
日期：2026-08-06
发送人：Claude（Agent）
接收人：max（研究者）
Project ID：PRJ-002（cadence）/ v0.3 Phase 2（RCP）

## Scope

本 WP 两个目标：
1. **启动 v0.2 Weekly/Monthly cadence**（ACT-20260729-009 的 Weekly 部分）
2. **起草 Phase 2 的两个 RCP**（RCP-v03-004/005）供 max 审

## Rules and templates read

- `07_Templates/Weekly_Review.md`、`Monthly_Review.md`
- `05_Research/Projects/PRJ-002/Reviews/README.md`（cadence 记录审计行格式）
- `03_Phase_2_Intelligence_Ingestion.md`（Channel/Candidate schema 草案、B-001/002）
- `05_Research/Reviews/Proposals/RCP-v03-003_...md`（RCP 格式模板）
- `08_Agent_Execution_Protocol.md`、`07_Templates/Research_Handoff.md`

## Objects created or changed

| Object | Action | Path | 说明 |
|---|---|---|---|
| Weekly review 记录 | 新增 | `05_Research/Projects/PRJ-002/Reviews/Weekly/WK-20260806-prj002.md` | completed（max 2026-08-06）|
| Metrics snapshot | 新增 | `05_Research/Reviews/Snapshots/METRICS-20260806.json` | 不可变快照 |
| RCP-v03-004 | 新增 | `05_Research/Reviews/Proposals/RCP-v03-004_Candidate_SQLite_and_Retention.md` | proposed |
| RCP-v03-005 | 新增 | `05_Research/Reviews/Proposals/RCP-v03-005_Source_Channel_and_Scheduler.md` | proposed |
| Pilot_Gate 更新 | 修改 | `05_Research/Projects/PRJ-002/Pilot_Gate.md` | Weekly 1/2 |
| 项目索引重建 | 修改 | `08_Indexes/Projects/PRJ-001/`、`PRJ-002/` | 修复 PRJ-002 drift |

## Facts established

- **v0.2 release 13/18 → 14/18**：修复 PRJ-002 index drift（indexes.pilot BLOCKED 解决）；
  第一个 Weekly completed（weekly 显示 "1 completed"）。
- 剩余 BLOCKED：weekly 1/2、monthly 0/1（真实时间项）、ACT-20260729-009、
  release.human_decision。

## Inferences proposed

- cadence 已启动：第二个 Weekly（8-12）与 Monthly（8-29）按 ACT-20260729-009
  时间表推进，8-29 前完成即可满足 release Gate。
- 两个 RCP 供 max 审：RCP-v03-004（Candidate SQLite 事实边界）+ RCP-v03-005
  （Channel/scheduler/许可边界）。

## Conflicts and unknowns

- 无冲突。validate 0 error；index 全 PASS；120 tests。
- RCP 状态为 proposed，待 max 审批。

## Human decisions required

- **RCP-v03-004 / RCP-v03-005 审批**（各含 4 个 review points）。
- 第二个 Weekly（8-12）与 Monthly（8-29）完成。

## Verification

- Validate：0 errors / 0 warnings
- Index：global + PRJ-001 + PRJ-002 全 PASS
- Tests：120 passed
- release check：14/18（weekly 1 completed）

## Recommended next action

- **审批 RCP-v03-004/005** → WP-200/201 启动（Candidate DB + Channel Registry）
- 或 v0.2 第二个 Weekly（8-12 自动到期）
