# B-026 Phase 2 Acceptance Checklist

状态：`in_progress`（14-day Pilot 结束后由 max 判定）
开始：2026-08-06；目标完成：2026-08-20（Day 14）

每个 Gate 项映射到证据源；除注明"人工"外均由 CLI/自动化产生。

## Gate 判定标准（§12）

| # | Gate | 证据源 | 判定 | 记录 |
|---|---|---|---|---|
| G1 | ≥20 reviewed+enabled Channel | `channels list/check` | ⬜ | 20/20（Day 1 达成）|
| G2 | 每日任务按计划完成或留明确失败 | `pilot status` job_failures + launchd sweep.log | ⬜ | 依赖 launchd 持续 |
| G3 | 无静默漏跑 | `pilot status` stale/never-run + 每日 brief 是否生成 | ⬜ | 待观察 |
| G4 | 重复入队比例 <15% | `pipeline metrics` duplicate rate | ⬜ | 基线 50% |
| G5 | Top-20 人工相关性 ≥75% | 每日记录人工抽样判定 | ⬜ | 人工 |
| G6 | ≥20 Candidate 提升为正式 Source | `pilot status` promoted 计数 + `candidates list --status promoted` | ⬜ | **68/20（Day 1 达成）**|
| G7 | 提升 Source 通过资产/hash 检查 | `source verify-assets` 全 OK | ⬜ | 26 个新 Source 全 OK |
| G8 | 候选摘要不作 reviewed Fact | Daily Brief `unreviewed candidate` 标记 + 审阅流程审查 | ⬜ | 已机制化 |
| G9 | 每日 triage 中位耗时 ≤45min | 每日记录耗时 | ⬜ | 人工 |
| G10 | 失败与许可限制写入 Known Limitations | Known_Limitations_v0.2.md | ⬜ | github/SEC 缺口已记 |

## 判定流程

1. Day 14（或提前满足全部条件）跑：
   ```bash
   research-os pilot status --since 2026-08-06
   research-os pipeline metrics --as-of $(date +%F)
   research-os source verify-assets
   research-os channels check
   ```
2. 逐项核对上表，全部通过 → WP-240 completed，Phase 2 验收。
3. 未通过项 → 记录差异与修复计划（gate 不 pass 则 Phase 2 不 close）。

## 已知未达标风险（Day 1 暴露）

- ~~**G1 4/20**~~ ✅ **20/20 达成**（Day 1，7 SEC + 5 GitHub + 6 arXiv + 2 原通道）。
- **G4 50%**：SK hynix 多 URL 变体噪声；按 cluster 代表 promote 可缓解，
  目标 <15% 需在 feed 解析/去重上继续收紧。
- ~~**G6 0/20**~~ ✅ **26/20 达成**（Day 1，26 个 SEC 10-K/10-Q promote）。

## 验收记录

| 日期 | 判定人 | 结果 | 备注 |
|---|---|---|---|
| 2026-08-06 | | in_progress | Pilot 启动 |
