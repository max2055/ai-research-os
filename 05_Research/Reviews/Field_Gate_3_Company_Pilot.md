# Field Gate: 3-Company Decision Pilot（E-021，WP-520）

**日期**: 2026-08-09  **评审人**: max（待人工审核后确认）
**规则**: RCP-v03-009 Phase 5 §13 — 至少两个不同板块；完整 Company/Security/Valuation/Scenario/Forecast/Recommendation Draft；
每家公司至少一个核心反面 Thesis；价格和市场预期 freshness 合格；人工批准最高到 investment_candidate；不自动交易。

## 三家公司（3 个板块）

| Company | Sector | Security | Valuation | Forecast | Scenario | 反面 Thesis | Recommendation |
|---|---|---|---|---|---|---|---|
| COM-nvidia | SEG-compute-silicon | INS-NASDAQ-NVDA | 223.96 USD as-of 2026-08-07 (license: yahoo-finance-free-delayed) draft/reviewed | FCT-20260809-001 open/reviewed | Scenario_NVIDIA_20260809.md | THS-009 active/reviewed | REC-20260809-001 active/reviewed |
| COM-micron | SEG-memory-storage | INS-NASDAQ-MU | 877.57 USD as-of 2026-08-07 (license: yahoo-finance-free-delayed) draft/reviewed | FCT-20260809-005 open/reviewed | Scenario_Micron_20260809.md | THS-010 active/reviewed | REC-20260809-002 active/reviewed |
| COM-tsmc | SEG-foundry-packaging-test | INS-NYSE-TSM | 420.04 USD as-of 2026-08-07 (license: yahoo-finance-free-delayed) draft/reviewed | FCT-20260809-010 open/reviewed | Scenario_TSMC_20260809.md | THS-011 active/reviewed | REC-20260809-003 active/reviewed |

## 板块覆盖

- SEG-compute-silicon（NVIDIA）、SEG-memory-storage（Micron）、SEG-foundry-packaging-test（TSMC）— 3 个板块 ✓

## 完整性检查（E-021）

- **Company**: 均存在（COM-nvidia / COM-micron / COM-tsmc）✓
- **Security**: 均关联（NVDA / MU / TSM ADR）✓
- **Valuation**: 市场价快照（provider=Yahoo Finance, data_license=yahoo-finance-free-delayed, as_of=2026-08-07, freshness_threshold 7d）✓
- **Scenario**: 三情景 worksheet（Downside/Base/Upside + 两变量敏感性 + 证伪条件）✓
- **Forecast**: 每家公司至少 1 个 open reviewed Forecast ✓
- **Recommendation Draft**: 3 个 active（research posture, 最高未超 investment_candidate）✓
- **反面 Thesis**: 每家公司 1 个 reviewed 反面 Thesis（THS-009/010/011）✓
- **不交易**: 无 buy/sell/position-size, §7 ceiling 合规 ✓

## 判定表（人工确认）

| Company | 判定 | 备注 |
|---|---|---|
| NVIDIA | ⬜ | 定价权受供给/客户集中度约束（反面 THS-009） |
| Micron | ⬜ | 内存周期下行风险（反面 THS-010） |
| TSMC | ⬜ | 先进节点客户集中/地缘风险（反面 THS-011） |

## 解析 Gate 说明

- 首批 Forecast 自然到期后评价（WP-530），不得预填未来结果。
- Phase 工程能力可先 accepted；v0.3 final release 必须包含真实 resolution。
