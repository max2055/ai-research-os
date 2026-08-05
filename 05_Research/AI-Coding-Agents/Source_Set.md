# PRJ-002 Source Set v0.1

状态：`pending human review`

采集日期：2026-07-29

范围：AI Coding Agent 价值链与商业化

## 配额结果

| 类别 | 目标 | 当前 | 说明 |
|---|---:|---:|---|
| archived / processed Source | 10–15 | 12 | 全部含本地 raw、metadata、extracted text 和 extraction metadata |
| A 级来源 | ≥6 | 9 | 官方产品/定价/研究与同行评审论文 |
| 独立客户或团队采用 | ≥2 | 2 | Spotify、Meta 工程团队 |
| 方法透明的评测或研究 | ≥2 | 4 | DORA、METR 2025、METR 2026、PMLR |
| supporting 与反面材料 | 必须均有 | 有 | 生产部署/产品形态与 RCT slowdown/测量不确定性并存 |

以上是系统盘点，不代表 Source 内容已经通过人工真实性或解释性评审。

## Source inventory

| Source ID | Grade | Evidence role | Event | 主要限制 |
|---|---|---|---|---|
| `SRC-20260729-021` | A | GitHub session pricing 与 Actions 用量 | `EVT-20250820-016`, `EVT-20251002-017` | 厂商定价公告，无成本和留存数据 |
| `SRC-20260729-022` | A | Anthropic seat、extra usage 与治理控制 | `EVT-20250820-016` | 厂商公告与客户引语，未独立核验 |
| `SRC-20260729-023` | A | Google Jules 异步 VM→PR 架构 | `EVT-20251002-017` | 无成功率、合并率或干预率 |
| `SRC-20260729-024` | A | Cursor subscription + usage credit | `EVT-20250820-016` | 无单位经济性和 cohort 数据 |
| `SRC-20260729-025` | A | OpenAI Codex sandbox、验证和人工检查 | `EVT-20251002-017` | system card，不含商业化数据 |
| `SRC-20260729-026` | B | Spotify 生产部署与 1,500+ merged PR | `EVT-20251106-018` | 单公司自述，无 attempted-task denominator |
| `SRC-20260729-027` | B | Meta proprietary context layer | `EVT-20260406-019` | 初步测试仅六项任务 |
| `SRC-20260729-028` | A | 开发者采用、信任与自报生产率 | `EVT-20250729-020` | 横截面自报调查，不能识别因果 |
| `SRC-20260729-029` | A | DORA organizational amplifier framing | `EVT-20250923-021` | 已归档页缺少完整报告方法 |
| `SRC-20260729-030` | A | METR early-2025 RCT slowdown | `EVT-20250710-022` | 16 名资深维护者，工具代际受限 |
| `SRC-20260729-031` | B | METR later-study selection limits | `EVT-20260224-023` | 作者明确称当前效应信号不可靠 |
| `SRC-20260729-032` | A | ICML repository benchmark distribution | `EVT-20250713-024` | `published_date_proposal` 与会议日期仍待人工确认 |

## Balance by Thesis

| Thesis | Supporting / contextual evidence | Contradicting / limiting evidence | 当前判断边界 |
|---|---|---|---|
| `THS-006` | GitHub / Google / OpenAI 的异步 task layer；Spotify 生产部署 | METR 2025 slowdown；Stack Overflow 尚非多数采用；METR 2026 测量不确定性 | 形态存在，但普遍生产率与渗透率未确认 |
| `THS-007` | Spotify harness；Meta context；DORA organizational system；PMLR evaluation distribution | Meta 转述熟悉开源库中 context file 的反面结果 | 尚缺直接归档的标准化/可替代性研究 |
| `THS-008` | GitHub / Anthropic / Cursor 混合计费 | Spotify 明示规模化计算成本；METR 2025 slowdown；METR 2026 不能量化当前 uplift | 缺少 vendor gross margin 与 task-level cost 数据 |

## Provenance and processing

- 12 个 Source 均由 M3 capture/process 路径创建。
- 每个 Source 均登记 canonical URL、publisher、published/accessed date、local asset paths、capture time 和 SHA-256。
- Event Fact 由结构化 spec 生成，quote、asset、line locator 和 quote hash 已通过机器校验。
- Source 与 Event 均保持 `review_status: pending`；机器校验不构成人工批准。

## Capture exception

OpenAI pricing 网页在标准抓取和一次普通重试中返回 Cloudflare `403`，没有绕过访问控制，
也没有登记不完整 Source。用可直接访问的 OpenAI Codex system card 替代产品架构证据；
定价问题由 GitHub、Anthropic 和 Cursor 的可归档官方材料覆盖。若后续有许可明确且可复核的
OpenAI 定价材料，再作为新 Source 进入，而不是覆盖现有对象。

## Human review remaining

1. 完成 `M4_Field_Review_Packet.md` 的 10-Source Fact accuracy 检查。
2. 对 9 个 pending Event 分别执行 approve / edit / reject Review Decision。
3. 确认 `SRC-20260729-032` 的正式 publication date，处理 metadata proposal。
4. 补充 THS-007 的直接标准化/可替代性反证。
5. 在 reviewed Evidence 形成前，不调整 THS confidence。
