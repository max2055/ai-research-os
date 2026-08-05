# WP-011 Charter Decision Options

状态：`updated`（D1–D9 已拍板；D10–D12 为触发型决策，未触发）
日期：2026-08-05（决策日）
依赖：WP-000 基线、WP-010 RCP-v03-001（已 approved）

以下决策来自 `01_Product_Charter_and_Governance.md` §10 Gate 与 `00_Master_Roadmap.md` §9 关键人工决策点。每项均由研究者 max 明确拍板；Agent 不代替决定。

## 决策清单

| # | 决策 | 选项 | 决定 | 依据 | 最晚时间 | 决策 |
|---|---|---|---|---|---|---|
| D1 | 接受/修改 v0.3 产品定位（AI Industry Intelligence & Decision OS） | 接受 / 修改 / 拒绝 | **接受** | Charter §1、Roadmap §1 | 阶段 0 前 | 2026-08-05 max |
| D2 | v0.2 cadence 与 v0.3 先后 | 并行 / 先收尾 v0.2 | **并行** | Charter §10、M6 状态 | 阶段 0 前 | 2026-08-05 max |
| D3 | 第一个 Pilot value chain | AI Compute Infra / Model-Agent-Enterprise / 其他 | **AI Compute Infrastructure Chain** | Roadmap §8 建议 Pilot | 阶段 0 前 | 2026-08-05 max |
| D4 | Universe Core 规模上限 | 30–50 / 20–30 / 50–80 | **30–50**；上限未经批准不得扩大 | Phase 0-1 §6、Backlog 风险登记 | 阶段 1 写入前 | 2026-08-05 max |
| D5 | Candidate store 是否用 SQLite | SQLite / 先不上数据库 | **SQLite**（可重建 operational store，非事实源） | Charter §5.3 | 阶段 2 前 | 2026-08-05 max |
| D6 | Sector ID 前缀 | `SEG` / `SEC` | **`SEG`**（避免与美国 SEC Adapter 混淆） | Charter §7 | 阶段 1 写对象前 | 2026-08-05 max |
| D7 | Recommendation 最高权威等级 | 人工批准 / 仅 Watch | **人工批准、不得自动执行** | Charter §3、§6 | 阶段 5 前 | 2026-08-05 max |
| D8 | 批准 RCP-v03-001 | 批准 / 修改后批准 / 拒绝 | **批准（approved）** | — | 任何 v0.3 编码前 | 2026-08-05 max |
| D9 | RCP-v03-002~010 reviewer 与计划日期 | 默认 Wave / 逐项 / 滚动 | **按默认 Wave 排期**；reviewer 统一 max，各阶段开始前补人审 | Charter §8、Backlog §3 | 阶段 0 Gate 时 | 2026-08-05 max |
| D10 | 是否扩大 Universe | 每个 Pilot Gate 后评估 | 触发型：未触发 | Roadmap §9 | 每个 Pilot Gate 后 | pending |
| D11 | 是否采用 PostgreSQL/图数据库 | 量化瓶颈触发后 | 触发型：未触发 | Roadmap §9、Backlog 风险 | 触发瓶颈后 | pending |
| D12 | v0.3 发布决定 | 30 天 Pilot 后 | 触发型：未触发 | Roadmap §9 | 30 天 Pilot 后 | pending |

## 阶段 0 Gate 检查（Charter §10）

- [x] D1 接受产品定位（2026-08-05 max）
- [x] D2 并行推进（2026-08-05 max）
- [x] D3 Pilot = AI Compute Infrastructure Chain（2026-08-05 max）
- [x] D4 Universe Core 上限 30–50（2026-08-05 max）
- [x] D5 Candidate store 使用 SQLite（2026-08-05 max）
- [x] D6 Sector ID 前缀 = SEG（2026-08-05 max）
- [x] D7 Recommendation 最高等级 = 人工批准、不自动执行（2026-08-05 max）
- [x] D8 批准 RCP-v03-001（2026-08-05，reviewer：max；详见 `05_Research/Reviews/Proposals/RCP-v03-001_...md`）
- [x] D9 RCP-v03-002~010 按默认 Wave 排期，reviewer=max（2026-08-05 max）

阶段 0 Gate 的 Charter 内人工选择已全部完成，可进入 WP-100（Taxonomy v1 使用审计）等只读/文档工作包；具体 Schema/ID/Taxonomy 实施仍需对应 RCP（002/003…）逐项批准。

## RCP-v03-002~010 排期（按默认 Wave）

reviewer 统一：max。计划日期 = 对应阶段开始前（滚动）；此处只锁顺序与阶段归属。

| RCP | 主题 | Wave / 阶段 | 何时审批 |
|---|---|---|---|
| RCP-v03-002 | Taxonomy v2 与稳定板块 ID | Wave 1（Phase 0-1） | Phase 1 migration 前 |
| RCP-v03-003 | 新实体 Schema 与永久 ID | Wave 1（Phase 0-1） | Phase 1 写对象前 |
| RCP-v03-004 | Candidate SQLite 与 retention | Wave 2（Phase 2） | Phase 2 写数据库前 |
| RCP-v03-005 | Source Channel、scheduler、许可边界 | Wave 2（Phase 2） | Phase 2 自动运行前 |
| RCP-v03-006 | Ontology/Impact 关系语义 | Wave 3（Phase 3） | Phase 3 写 assertion 前 |
| RCP-v03-007 | Analysis Mode 与 Analysis Run 权威边界 | Wave 4（Phase 4） | Phase 4 前 |
| RCP-v03-008 | Forecast、Resolution、calibration | Wave 5（Phase 5） | Phase 5 前 |
| RCP-v03-009 | Recommendation 等级与人工批准规则 | Wave 5（Phase 5） | Phase 5 前 |
| RCP-v03-010 | v0.3 数据库、备份、恢复策略 | Wave 6（Phase 6） | Phase 6 发布前 |

## 说明

- 本文件为决策清单；决定记于上表"决策"列与下方决策日志（Backlog §13 模板）。
- 任何未被批准的新 Schema、永久 ID、事实源变更不实施。
- 触发型决策（D10–D12）在触发时再拍，不提前回填。