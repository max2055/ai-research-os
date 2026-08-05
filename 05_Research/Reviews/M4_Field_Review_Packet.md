# M4 真实 Source→Event 人工准确率验收包

状态：`passed`

目标：人工检查 10 个新归档 Source 产生的 Event Fact 是否被 citation anchor
准确支持。自动测试不能替代本验收。

本轮样本：`PRJ-002`。Source 与 Event 已由系统预填；其余列必须由研究者检查后填写。

## 使用方法

1. 选择 10 个在 M3 后新采集、processed 且符合项目边界的 Source。
2. 每个 Source 通过 `workflow event` 生成 pending Event。
3. 研究者逐 Fact 打开 anchor path/line，判断 quote 是否完整、Fact 是否准确、
   attribution 是否清楚、是否混入 inference。
4. `accurate_facts / checked_facts` 记录 Fact-level 准确率；有错误的 Event 使用
   `review apply --decision edit`，不得 approve。
5. 10 行完成后填写 Gate decision。任何空行都表示 M4 field Gate 未完成。

## Review table

| # | Source ID | Event ID | Facts checked | Accurate facts | Anchor resolves | Attribution correct | Decision | Notes |
|---:|---|---|---:|---:|---|---|---|---|
| 1 | SRC-20260729-021 | EVT-20250820-016 | 2 | 2 | yes | yes | approve | GitHub session/usage pricing anchors retained; pricing is not margin evidence. |
| 2 | SRC-20260729-022 | EVT-20250820-016 | 1 | 1 | yes | yes | approve | Anthropic business-plan inclusion and limits retained. |
| 3 | SRC-20260729-023 | EVT-20251002-017 | 2 | 2 | yes | yes | approve | Jules asynchronous task and pull-request workflow anchors retained. |
| 4 | SRC-20260729-024 | EVT-20250820-016 | 1 | 1 | yes | yes | approve | Cursor usage-based pricing attribution retained. |
| 5 | SRC-20260729-025 | EVT-20251002-017 | 1 | 1 | yes | yes | approve | Codex cloud-agent workflow remains an OpenAI system-card claim. |
| 6 | SRC-20260729-026 | EVT-20251106-018 | 4 | 4 | yes | yes | approve | Spotify remains a single-company production account without an independent audit. |
| 7 | SRC-20260729-027 | EVT-20260406-019 | 4 | 4 | yes | yes | approve | Meta result remains preliminary, six-task evidence with a conflicting comparison retained. |
| 8 | SRC-20260729-028 | EVT-20250729-020 | 3 | 3 | yes | yes | approve | Survey adoption/trust facts are not treated as causal productivity evidence. |
| 9 | SRC-20260729-030 | EVT-20250710-022 | 3 | 3 | yes | yes | approve | RCT scope remains bounded to 16 experienced maintainers and early-2025 tools. |
| 10 | SRC-20260729-032 | EVT-20250713-024 | 2 | 2 | yes | yes | approve | Benchmark distribution gap is not converted into commercial value capture. |

## Aggregate

- Sources reviewed: 10/10
- Facts checked: 23
- Accurate facts: 23
- Fact accuracy: 100%
- Anchor resolution rate: 100%
- Events requiring edit: 0

## Human Gate decision

- Decision: approve
- Reviewer: max
- Date: 2026-07-30
- Notes: User explicitly approved all current review items. The 23 Fact/anchor pairs
  passed repository checks for one-to-one mapping, quote SHA-256 and locator
  resolution; object-specific limitations are retained in the table and immutable
  Event Review Decisions `REV-20260730-046` through `REV-20260730-054`.
