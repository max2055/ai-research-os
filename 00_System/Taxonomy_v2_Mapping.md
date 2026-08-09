# Taxonomy v1 → v2 Mapping（A-002 使用审计）

状态：`approved / authoritative mapping`（RCP-v03-002，2026-08-05，max）
创建日期：2026-08-05
工作包：WP-100 / A-002（只读审计 + 映射提案，不修改任何规则或对象）
依赖：`00_System/Taxonomy.md`（v0.1）、`02_Phase_0_1_Ontology_and_Universe.md` §3

> 本文件是 RCP-v03-002 已批准的审计输出与 v1→v2 权威映射。
> 按 Taxonomy §5，后续修改现有分类含义、合并或废弃稳定标签、改变历史对象使用的
> 标签仍需新的人审决定。本映射不改动任何 v0.2 对象的 tag。

## 1. 审计方法

扫描 `02_Knowledge / 03_Theses / 04_Evidence / 05_Research / 06_Reports / 01_Inbox`
（排除 `migrations/backups`、`07_Templates`、`00_System`），用正则
`\b(INF|MOD|DEV|APP|SRV|MAT|CUS|BM|MOAT|EV)-[A-Z0-9-]+` 抓取 frontmatter
与正文中的标签，并与 `Taxonomy.md`（v0.1）定义集比对。

**重要口径**：`MOD-ANL` 仅出现在 v0.3 规划文档（`05_Research/Reviews/Proposals/`
与 `00_System/v0.3_.../05_Phase_4_...md`），**不在任何 v0.2 正式研究对象的
frontmatter**。它是 v0.3 新增前缀（Analysis Mode），已由 RCP-v03-003/007
批准，**不属于 v0.1 治理债**，不计入下表的 used-but-undefined。

## 2. 审计结果

- **定义**：93 个标签（Taxonomy v0.1）
- **实际使用**：41 个（全部在 frontmatter，正文零使用——口径一致，无散落）
- **定义但未使用**：53 个
- **使用但未定义**：0（v0.2 正式对象意义上）

### 2.1 使用中的标签（按频次）

| Tag | 用次 | 主要对象 | 说明 |
|---|---:|---|---|
| DEV-AGENT-FRAMEWORK | 65 | event/other | PRJ-002 主线，最重 |
| DEV-ORCHESTRATION | 41 | event/other | PRJ-002 主线 |
| APP-CODING | 30 | event/other | PRJ-002 主线（coding agent） |
| DEV-EVALUATION | 22 | event | Agent 评测 |
| EV-PRODUCT | 22 | event | 事件类型 |
| EV-CUSTOMER | 21 | event | |
| MAT-PRODUCTION | 17 | event | 成熟度 |
| MOAT-WORKFLOW | 16 | event/entity | |
| APP-CRM | 16 | event/entity | PRJ-001 |
| EV-FINANCIAL | 16 | event | |
| EV-TECHNOLOGY | 16 | event | |
| MOAT-DATA | 14 | event/entity | |
| DEV-TOOL-PROTOCOL | 12 | event | |
| MOAT-PERMISSION | 12 | event/entity | |
| APP-ERP | 11 | event/entity | |
| DEV-DATA | 10 | event | |
| EV-PRICING | 10 | event | |
| MAT-RESEARCH | 9 | event | |
| BM-SEAT | 8 | event/other | |
| DEV-SECURITY | 8 | event | |
| CUS-DEVELOPER | 7 | other | |
| BM-USAGE | 7 | other | |
| CUS-ENTERPRISE | 7 | other | |
| INF-CLOUD-AI | 6 | entity/event | 唯一进入使用的 INF 标签 |
| APP-ENTERPRISE | 5 | other | |
| MOD-FOUNDATION | 4 | entity/event | |
| DEV-MEMORY | 4 | other/event | |
| MOAT-ECOSYSTEM | 4 | other | |
| BM-TASK | 4 | other | |
| MAT-PROTOTYPE | 4 | event | |
| MAT-PILOT | 4 | event | |
| APP-ITSM | 3 | | |
| APP-COLLABORATION | 3 | | |
| MAT-SCALE | 3 | event | |
| EV-PARTNERSHIP | 3 | | |
| MOAT-DISTRIBUTION | 2 | | |
| EV-COMPETITION | 2 | | |
| DEV-INFERENCE | 2 | | |
| BM-SUBSCRIPTION | 2 | | |
| BM-OUTCOME | 1 | | |

### 2.2 定义但未使用（53 个，按前缀）

- **INF-**（24 个，**几乎整个基础设施层零使用**）：INF-ASIC, INF-CLOUD, INF-CLOUD-COMPUTE, INF-COMPUTE, INF-COOLING, INF-CPU, INF-DATACENTER, INF-DATACENTER-NETWORK, INF-DRAM, INF-EDGE, INF-ENERGY, INF-GPU, INF-HBM, INF-INTERCONNECT, INF-MEMORY, INF-NETWORK, INF-POWER, INF-SERVER, INF-STORAGE
- **MOD-**（5）：MOD-EMBEDDING, MOD-MULTIMODAL, MOD-OPEN, MOD-REASONING, MOD-SMALL
- **DEV-**（1）：DEV-TRAINING
- **APP-**（11）：APP-ASSISTANT, APP-CONSUMER, APP-CONTENT, APP-CYBERSECURITY, APP-DATA-ANALYTICS, APP-DESIGN, APP-EDUCATION, APP-HCM, APP-KNOWLEDGE, APP-LEGAL, APP-RESEARCH, APP-VERTICAL
- **SRV-**（4，全零）：SRV-CONSULTING, SRV-DATA-LABELING, SRV-INTEGRATION, SRV-MANAGED
- **MOAT-**（4）：MOAT-BRAND, MOAT-REGULATION, MOAT-SCALE, MOAT-TECHNOLOGY
- **EV-**（3）：EV-CAPITAL, EV-MANAGEMENT, EV-REGULATION
- **CUS-**（3）：CUS-CONSUMER, CUS-GOVERNMENT, CUS-SMB
- **BM-**（2）：BM-SERVICE, BM-TRANSACTION

## 3. 结构性发现

1. **基础设施层（INF-*）几乎全废**：24 个定义里只有 `INF-CLOUD-AI` 实际使用（6 次，且多挂在 COM-microsoft）。这与 v0.2 只覆盖企业软件单专题一致；D3 选 "AI Compute Infrastructure Chain" 为第一 Pilot，正是要把这层从定义推进到使用。
2. **横向维度层健康**：MAT / CUS / BM / MOAT / EV 实际是 v0.2 用得最多的层（事件类型、商业模式、护城河、成熟度、客户），与 Phase 0-1 §3"横向维度继续使用并扩展"一致 → v2 全部 keep 并扩展。
3. **DEV-/MOD-/APP- 的产业细分 vs v0.3 扇区制**：v0.1 用扁平 tag 表达产业细分（INF-GPU、APP-CRM），v0.3 Phase 0-1 §3 改用 **Sector 实体（SEG-ID）+ Technology/Product 实体** 表达产业归属。因此大量 INF 细分 tag 在 v2 倾向 **map 到实体引用并 deprecate 作为 tag**，而不是保留。
4. **`APP-CODING`（30 次，PRJ-002 主线）**：v0.1 把它放在 "知识工作" 子类，但实际是 PRJ-002 的核心赛道。v2 需要把它升格或在 Sector 体系里给 AI Coding 一个明确扇区位置，不能静默降级。
5. **`INF-CLOUD-AI` 唯一进入使用的 INF 标签**：跨在 "云" 与 "AI 平台" 之间，v2 扇区里对应 "Cloud & AI Infrastructure"，需明确边界避免与 "Models" / "Data & AI Development" 重叠。

## 4. 映射决定（proposal，每个旧 tag）

图例：**keep** 保留为 tag；**map** 迁移到新表达（Sector/Technology/Product 实体引用），tag 退役；**deprecate** 废弃（v0.1 未用或语义被实体取代）；**rename** 改名（仅命名，不改语义，需 RCP）。

### 4.1 产业层 INF / MOD / DEV / APP / SRV

| 旧 tag | 决定 | v2 落点 | 理由 |
|---|---|---|---|
| INF-GPU, INF-ASIC, INF-CPU, INF-EDGE | map | Sector=Compute Silicon + Technology 实体（GPU/ASIC/CPU/edge） | 产业细分由实体表达，tag 退役 |
| INF-HBM, INF-DRAM, INF-STORAGE | map | Sector=Memory & Storage + Technology 实体 | 同上 |
| INF-INTERCONNECT, INF-DATACENTER-NETWORK | map | Sector=Server Network & Interconnect | 同上 |
| INF-SERVER, INF-COOLING, INF-POWER, INF-ENERGY | map | Sector=Datacenter Infrastructure | 同上 |
| INF-CLOUD-COMPUTE, INF-CLOUD, INF-CLOUD-AI | **keep INF-CLOUD-AI；map 其余** | Sector=Cloud & AI Infrastructure | INF-CLOUD-AI 有使用，保留；其余 map 到扇区 |
| INF-COMPUTE, INF-MEMORY, INF-NETWORK, INF-DATACENTER | deprecate | 父类已被扇区取代 | 仅作聚合用，无独立语义 |
| MOD-FOUNDATION, MOD-REASONING, MOD-MULTIMODAL, MOD-SMALL, MOD-OPEN, MOD-EMBEDDING | map（MOD-FOUNDATION keep 候选） | Sector=Models + Technology 实体 | 模型类型由 Technology 实体表达；MOD-FOUNDATION 有 4 次使用，RCP 决定 keep 或 map |
| DEV-TRAINING, DEV-INFERENCE, DEV-EVALUATION, DEV-DATA, DEV-SECURITY | keep（DEV-EVALUATION 高频） | Sector=Data & AI Development；DEV-* 作 Technology 实体 tag | 评测/训练/推理是稳定维度，keep |
| DEV-AGENT-FRAMEWORK, DEV-TOOL-PROTOCOL, DEV-MEMORY, DEV-ORCHESTRATION | **keep** | Sector=Data & AI Development 下 Agent runtime 子域 | PRJ-002 主线高频，v2 必须保留为稳定 tag |
| APP-CRM, APP-ERP, APP-ITSM, APP-HCM, APP-COLLABORATION, APP-DATA-ANALYTICS, APP-CYBERSECURITY, APP-VERTICAL | keep | Sector=Enterprise Applications；细分作 Product 实体 tag | PRJ-001 用中，保留 |
| APP-CODING | **keep + 升格** | Sector=Enterprise Applications 下 AI Coding 子域（明确位置） | 30 次使用，PRJ-002 主线，不能降级 |
| APP-RESEARCH, APP-DESIGN, APP-LEGAL | keep | Enterprise Applications / 知识工作 | 未用但语义清晰，v3 Pilot 用 |
| APP-ASSISTANT, APP-CONTENT, APP-EDUCATION | keep | Sector=Consumer Applications | 未用，为第二 Pilot 保留 |
| APP-ENTERPRISE, APP-CONSUMER, APP-KNOWLEDGE | deprecate（聚合类） | 由 Sector 扇区取代 | 仅父类聚合，无独立语义 |
| SRV-CONSULTING, SRV-INTEGRATION, SRV-MANAGED, SRV-DATA-LABELING | keep | Sector=Services | 全未用但 v3 需要服务层，保留 |

### 4.2 横向维度 MAT / CUS / BM / MOAT / EV（全部 keep，按需扩展）

| 旧 tag | 决定 | 备注 |
|---|---|---|
| MAT-RESEARCH..SCALE（全部） | **keep** | 实际使用中，Phase 0-1 §3 明确扩展 |
| CUS-CONSUMER/SMB/ENTERPRISE/GOVERMENT/DEVELOPER | **keep** | 7 类，CUS-ENTERPRISE/DEVELOPER 已用 |
| BM-SEAT/SUBSCRIPTION/USAGE/TASK/OUTCOME/SERVICE/TRANSACTION | **keep**（BM-SERVICE/BM-TRANSACTION 未用但语义清晰，keep） | 商业模式是核心横向维度 |
| MOAT-TECHNOLOGY/DATA/DISTRIBUTION/WORKFLOW/PERMISSION/ECOSYSTEM/SCALE/BRAND/REGULATION | **keep** | MOAT-WORKFLOW/DATA/PERMISSION 等已用；未用项保留供 Pilot |
| EV-PRODUCT/PRICING/CUSTOMER/PARTNERSHIP/FINANCIAL/MANAGEMENT/TECHNOLOGY/REGULATION/CAPITAL/COMPETITION | **keep**（EV-CAPITAL/MANAGEMENT/REGULATION 未用但语义清晰） | 事件类型稳定维度 |

### 4.3 新增（v2 提案，需 RCP-v03-002 批准）

- 13 个 L1 扇区作为 **Sector 实体**（SEG-ID），而非 tag：Semiconductor Materials & Equipment、Foundry Packaging & Test、Compute Silicon、Memory & Storage、Server Network & Interconnect、Datacenter Infrastructure、Cloud & AI Infrastructure、Models、Data & AI Development、Enterprise Applications、Consumer Applications、Services、Physical AI。
- 横向维度扩展项：地区、供应风险、资本强度、周期属性、监管敏感度（Phase 0-1 §3 列出但 v0.1 未定义 ID）。

## 5. 边界项决定（reviewer：max，2026-08-05）

| # | 问题 | 决定 | 备注 |
|---|---|---|---|
| R1 | tag 退役 vs 历史对象回填 | **不回填，保留旧 tag**；mapping 表提供语义映射；需补 SEG 关系时人工逐批核 | Taxonomy §5 要求人审；Phase 0-1 §11 回滚要求 |
| R2 | APP-CODING 扇区归属 | **keep 为 tag**，归 Enterprise Applications 下 "AI Developer Tooling" 子域 | PRJ-002 主线 30 次使用；后续独立 Pilot 再升级 |
| R3 | MOD-* keep/map 取舍 | **全 map 到 Models 扇区下 Technology 实体** | 与 INF-* 一致 |
| R4 | INF-CLOUD-AI 边界 | **归 Cloud & AI Infrastructure**；边界 = 云端模型平台/推理服务；不与 Models/Data & AI Dev 重叠 | 唯一在用的 INF 标签 |
| R5 | 父类聚合 tag deprecate 后迁移 | **父类沿用 R1：不回填，保留旧 tag** | INF-COMPUTE/MEMORY/NETWORK/DATACENTER |
| R6 | SRV-DATA-LABELING 归属 | 默认归 Services；RCP-v03-002 现场定；若与 Data & AI Dev 重叠明显再调 | 本轮未触发 |

> 决定已写入 `Taxonomy_v2_Proposal.md` §6，并由 max 于 2026-08-05 批准生效。

## 6. 不做的事

- 不修改任何 v0.2 对象的 tag。
- 不直接新增或废弃任何历史对象中的 Taxonomy 标签（本文件是映射记录）。
- 不创建任何 Sector/Technology/Product 实体（需 RCP-v03-003）。
- 不回填历史 tag。

## 7. 给 RCP-v03-002 的输入

本映射表是 RCP-v03-002（Taxonomy v2 与稳定板块 ID）的证据底座：
- 确认 v0.1 哪些标签稳定（keep）、哪些被实体引用取代（map）、哪些废弃（deprecate）；
- 列出 13 个 L1 扇区与横向维度扩展项，供 RCP 起草 Taxonomy v2 定义（A-003）；
- 记录 5 个人工边界项及 RCP-v03-002 的逐项决定。
