# WP-011 Charter Decision Options

状态：`proposed`（整理给研究者拍板的选项，不编码、不实施）
日期：2026-08-05
依赖：WP-000 基线、WP-010 RCP-v03-001 草稿

以下决策来自 `01_Product_Charter_and_Governance.md` §10 Gate 与 `00_Master_Roadmap.md` §9 关键人工决策点。每一项都需要研究者明确决定；Agent 不代替决定。

## 决策清单

| # | 决策 | 选项 | 建议 | 依据 | 最晚时间 |
|---|---|---|---|---|---|
| D1 | 接受/修改 v0.3 产品定位（AI Industry Intelligence & Decision OS） | 接受 / 修改目标闭环 / 拒绝 | 接受，目标闭环见 Roadmap §1 | Charter §1、Roadmap §1 | 阶段 0 前 |
| D2 | v0.2 cadence 是否与 v0.3 并行完成 | 并行 / 先收尾 v0.2 | 并行：WP-001（Weekly/Monthly/发布决定）保持日期阻塞，v0.3 WP-000/010/011 只读/文档先行 | Charter §10、M6 状态 | 阶段 0 前 |
| D3 | 第一个 Pilot value chain | AI Compute Infrastructure Chain（建议）/ Model-Agent-Enterprise Apps / 其他 | AI Compute Infrastructure Chain（多板块、多公司、多跳关系、来源丰富、机制可观察） | Roadmap §8 建议 Pilot | 阶段 0 前 |
| D4 | Universe Core 规模上限 | 30–50（建议） / 其他 | 30–50；上限未经批准不得扩大 | Phase 0-1 §6、Backlog 风险登记 | 阶段 1 写入前 |
| D5 | Candidate store 是否使用 SQLite | SQLite（建议） / 其他 | SQLite 作为可重建 operational store，非事实源 | Charter §5.3 | 阶段 2 前 |
| D6 | Sector ID 前缀 | `SEG`（建议，避免与美国 SEC 混淆）/ `SEC` | SEG | Charter §7 | 阶段 1 写对象前 |
| D7 | Recommendation 最高权威等级 | 人工批准的个人研究建议（建议）/ 更高/更低 | 人工批准且不得自动执行 | Charter §3、§6 | 阶段 5 前 |
| D8 | 批准 RCP-v03-001 | 批准 / 修改后批准 / 拒绝 | 见 WP-010 草稿 | — | 任何 v0.3 编码前 |
| D9 | RCP-v03-002~010 的 reviewer 与计划日期 | 逐项指定 reviewer/日期 | 阶段 0 Gate 后排出 | Charter §8 | 阶段 0 Gate 时 |
| D10 | 是否扩大 Universe | 每个 Pilot Gate 后评估 | Gate 触发时决定 | Roadmap §9 | 每个 Pilot Gate 后 |
| D11 | 是否采用 PostgreSQL/图数据库 | 量化瓶颈触发后评估 | 先 SQLite/profile 再评估 | Roadmap §9、Backlog 风险 | 触发瓶颈后 |
| D12 | v0.3 发布决定 | 30 天 Pilot 后 | Pilot 数据决定 | Roadmap §9 | 30 天 Pilot 后 |

## 阶段 0 Gate 检查（Charter §10）

- [ ] D1 接受/修改产品定位
- [ ] D2 v0.2 cadence 并行与否
- [ ] D3 第一个 Pilot value chain
- [ ] D4 Universe Core 上限
- [ ] D5 Candidate store 使用 SQLite
- [ ] D6 Sector ID 前缀
- [ ] D7 Recommendation 最高权威等级
- [x] D8 批准 RCP-v03-001（2026-08-05，reviewer：max；状态 approved，详见 `05_Research/Reviews/Proposals/RCP-v03-001_...md`）
- [ ] D9 其余 RCP 指定 reviewer 和计划日期

## 说明

- 本文件仅为选项清单；研究者拍板后，决定记入对应 RCP/决策日志（Backlog §13 模板）。
- 任何未被批准的新 Schema、永久 ID、事实源变更不实施。
