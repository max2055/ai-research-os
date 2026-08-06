# 14-Day Pilot Kickoff（B-025）

开始日期：2026-08-06
目标：连续 14 天真实运行 Candidate Pipeline + 人工 triage，达成 §12 Gate，
随后 B-026 Phase acceptance。

## 基线（Day 1）

- **launchd 已安装并验证**：`com.aioresearchos.discovery`（每 6h + RunAtLoad）。
  第一轮真实运行：arxiv +20 候选、skhynix +10、github/SEC 失败（见下）。
- **候选队列**：50（SK hynix 30 + arXiv 20），全部 `new` 未审阅。
- **pipeline metrics（Day 1）**：dup rate 50%（25 非代表/25 cluster）、
  median latency 2.5s、failure_rate 待 github/SEC 修复后口径补全。
- **Daily Brief**：2026-08-06 已生成。

## Gate 清单（§12）与当前状态

| Gate | 目标 | Day 1 状态 |
|---|---|---|
| reviewed+enabled Channel | ≥20 | **20/20 ✅**（6 首批发 + 18 新：7 per-company SEC + 5 per-repo GitHub + 6 arXiv 分区；SEC/GitHub 聚合已禁用避免重复抓取）|
| 每日任务按计划完成或留明确失败 | 持续 | 依赖 launchd（已装）；github/SEC 每次失败留 Job 记录 |
| 不出现静默漏跑 | 持续 | 待观察（`pilot status` 的 job_failures + stale）|
| 重复入队比例 | <15% | 50%（SK hynix 多 URL 变体，promote 前按 cluster 代表处理）|
| Top-20 人工相关性 | ≥75% | 待每日 triage 记录 |
| ≥20 Candidate 提升为正式 Source | ≥20 | **70/20 ✅**（10-K/10-Q 26 + 重大 8-K 42 + github 模型信号 2）|
| 提升 Source 通过资产/hash 检查 | 全过 | `source verify-assets` 逐次检查 |
| 候选摘要不作 reviewed Fact | 硬性 | Daily Brief 已强制 `unreviewed candidate` 标记 |
| 每日人工 triage 中位耗时 | ≤45min | 待记录 |
| 失败与许可限制写入 Known Limitations | 持续 | 见下方已知缺口 |

## 已知配置缺口（2026-08-06 更新）

1. ~~**CHN-github-releases**：locator 是占位符模板~~ ✅ **已修复**：locator 改为
   5 个真实 repo URL（openai-python / anthropic-sdk-python / llama-models /
   DeepSeek-V3 / autogen），`CompositeDiscoveryAdapter` 支持多 repo。首轮验证
   +20 候选。
2. ~~**CHN-sec-edgar**：locator 无 CIK~~ ✅ **已修复**：locator 加
   `?cik=1045810,1046179,723125,789019,1326801,1018724,2015943`，query 清理为
   `10-K,10-Q,20-F`，composite 多 CIK。首轮验证 +20 候选。
3. ~~**Channel 数量 4/20**~~ ✅ **已补齐 20/20**（2026-08-06）：新增 18 个通道
   （7 per-company SEC + 5 per-repo GitHub + 6 arXiv 研究分区），batch review
   （REV-070）+ enable；SEC/GitHub 聚合已禁用（enabled: false）避免重复抓取。

> github repo 列表是默认选择，max 可调整；个别 CIK 若失效 composite 会跳过
> 不拖垮整通道。

## 每日例行（max）

```bash
# 1. 看今天要审什么（已自动生成）
research-os brief daily --date $(date +%F)     # 未生成时先 jobs run daily-brief

# 2. 审队列（按优先级，daily brief Top5 起）
research-os candidates list --limit 20
research-os candidates show --id <CND-ID>

# 3. triage
research-os candidates promote --id <CND-ID> --actor max --apply   # 可信候选提升
research-os candidates dismiss --id <CND-ID> --reason "<理由>" --actor max --apply

# 4. 看 Gate 进度
research-os pilot status --since 2026-08-06
research-os pipeline metrics --as-of $(date +%F)

# 5. 校验提升的 Source 资产
research-os source verify-assets
```

在下方"每日记录"表登记：审阅数、triage 中位耗时、Top-20 相关性抽样判定。

## 每日记录

| 日期 | 新候选 | 审阅数 | promote | dismiss | triage 耗时 | Top-20 相关性 | 备注 |
|---|---|---|---|---|---|---|---|
| 2026-08-06 | 395 | 198 | 70 | 128 | | | 26×10-K/10-Q + 42×重大 8-K + 2×github 模型信号（Llama4/gpt-5.5）；66 聚合/例行 + 62 例行 8-K + 63 例行 github |
