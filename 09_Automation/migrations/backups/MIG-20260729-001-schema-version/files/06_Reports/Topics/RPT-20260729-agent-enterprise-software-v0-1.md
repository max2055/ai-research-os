---
id: RPT-20260729-agent-enterprise-software-v0-1
type: report
title: AI Agent 时代，企业软件价值链是否正在重构？v0.1
created_at: 2026-07-29
updated_at: 2026-07-29
status: final
review_status: reviewed
report_type: topic
period_start: 2025-12-09
period_end: 2026-07-29
thesis_ids: [THS-001, THS-002, THS-003, THS-004, THS-005]
evidence_ids:
  - EVT-20260219-001
  - EVT-20260225-002
  - EVT-20260415-003
  - EVT-20260429-004
  - EVT-20260514-005
  - EVT-20260521-006
  - EVT-20260610-007
  - EVT-20260611-008
  - EVT-20260714-009
  - EVT-20260722-010
  - EVT-20260723-011
  - EVT-20260729-012
  - EVT-20260729-013
  - EVT-20260729-014
  - EVT-20260729-015
tags: [APP-ENTERPRISE, DEV-AGENT-FRAMEWORK, DEV-ORCHESTRATION]
---

# AI Agent 时代，企业软件价值链是否正在重构？v0.1

> 状态说明：本报告由 20 个 Source 和 15 张已审核 Event Card 综合生成，并于 2026-07-29 由研究者审核通过。它是一份主题研究结论，不构成个性化投资建议。

## One-sentence conclusion

**初步证据表明企业软件正在从“记录和展示工作的系统”向“理解意图并执行工作的系统”演进，但当前更可能发生的是入口、定价和控制权的渐进重构，而不是传统企业软件被快速替代。**

## Research question and scope

本报告研究：

- Agent 是否改变企业软件入口。
- 数据、权限和工作流是否成为核心护城河。
- 定价是否从席位迁移到使用、任务或结果。
- 现有厂商和 AI Native 厂商的相对优势。
- 是否正在形成跨系统 Agent 控制层。

不研究：

- 消费者 AI。
- AI 芯片完整投资逻辑。
- 全部垂直行业应用。
- 自动交易或买卖建议。

## Current value chain

```text
云和计算
→ 基础模型
→ Agent SDK / 运行时 / 协议
→ 企业数据、身份、权限和工作流
→ ERP / CRM / ITSM / 办公应用
→ Agent 入口与任务执行
→ 企业客户和最终用户
```

传统企业软件主要控制数据、系统记录、界面和工作流。模型厂商主要控制智能能力和新的对话入口。当前竞争焦点正在向两者之间的执行层移动。

## What is changing

### 1. Agent 从回答问题扩展到执行任务

OpenAI Agents SDK 增加计算机环境、沙箱和状态恢复（`EVT-20260415-003`）；Oracle、ServiceNow 和 Palantir 均把 Agent 与业务对象、工具、权限和工作流结合（`EVT-20260714-009`、`EVT-20260729-013`、`EVT-20260729-014`）。

**推断：** 单纯模型能力不足以完成企业任务，执行环境和可治理工具调用正在成为产品的一部分。

### 2. 现有厂商主动重构入口

SAP 将 Joule 嵌入 SAP for Me，并明确描述从点击和搜索向对话入口迁移（`EVT-20260611-008`）。ServiceNow 把 Otto 描述为跨系统路由并完成任务的统一入口（`EVT-20260729-013`）。

**推断：** 界面价值可能部分下降，但现有厂商并非被动等待颠覆，而是在用存量数据和分发重构自己的入口。

### 3. 定价出现混合化

Salesforce Agentforce 同时采用按 Action、Conversation 和用户席位收费（`EVT-20260729-012`）；Microsoft 特定 Copilot 促销仍围绕席位和覆盖率（`EVT-20260219-001`）。

**推断：** 定价变化不是“席位制立刻消失”，而是席位、用量和任务单位并存。未来收入质量取决于增量支出、推理成本和客户预算可预测性。

### 4. 商业验证开始出现，但指标仍不统一

Salesforce 披露 Agentforce ARR、交易和生产账户增长（`EVT-20260225-002`）；ServiceNow 披露 AI ACV 和 Agentic deployment 增长（`EVT-20260722-010`）。

**推断：** 企业 Agent 已越过纯概念阶段，但不同公司的指标定义、产品范围和基数差异很大，尚不能横向直接比较。

### 5. 开放协议同时推动互操作与去锁定

MCP 候选规范扩展长任务、应用和授权机制（`EVT-20260521-006`）。ServiceNow、Oracle、Palantir、OpenAI 和 Anthropic 均出现开放协议或第三方工具连接路径。

**推断：** 标准化可能帮助 Agent 跨系统执行，但也可能把连接器从专有护城河变为公共基础设施。最终价值可能留在数据、权限、工作流和用户入口。

## Thesis assessment

| Thesis | 初始置信度 | 当前草稿判断 | 关键 Evidence | 状态 |
|---|---:|---|---|---|
| THS-001 界面价值下降 | 0.25 | 有产品方向证据，缺少使用替代数据 | EVT-20260611-008 | 保持 |
| THS-002 企业上下文护城河 | 0.30 | 多家公司产品架构一致支持；开放协议构成反证 | EVT-20260714-009、013、014、006 | 报告已审核；置信度调整未执行，需单独决策 |
| THS-003 定价模式迁移 | 0.20 | Salesforce 明确采用混合计价；Microsoft 仍强化席位 | EVT-20260729-012、EVT-20260219-001 | 报告已审核；置信度调整未执行，需单独决策 |
| THS-004 现有厂商优势与冲突 | 0.30 | 分发优势已有商业指标，创新者困境尚未直接证明 | EVT-20260225-002、EVT-20260722-010 | 优势部分上调，冲突部分保持 |
| THS-005 Agent 控制层 | 0.20 | 多个平台争夺控制层，但尚无赢家和使用深度 | EVT-20260415-003、006、013、015 | 保持低置信度 |

## Incumbents versus AI Native challengers

| 类型 | 当前优势 | 当前约束 |
|---|---|---|
| Microsoft | 云、办公入口、身份、开发者和企业分发 | AI 收入构成不透明；与合作模型厂商竞合 |
| Salesforce | CRM 数据、工作流、现有客户、可披露 Agent ARR | 混合定价复杂；席位替代与毛利率未知 |
| ServiceNow | IT 工作流、CMDB、治理和 Control Tower 定位 | AI 指标口径宽；控制层使用深度未知 |
| Oracle | 数据库、Fusion 业务对象、权限和原生运行时 | Agent 商业化未拆分；资本开支主要来自基础设施 |
| SAP | ERP 数据、业务语义、核心流程和客户迁移成本 | 云迁移周期长；Agent 独立收入未披露 |
| Palantir | Ontology、读写运营工作流、权限和评测 | 实施复杂；Foundry Agents 仍为 Beta |
| OpenAI | 模型、开发者、ChatGPT 入口和 Agent 运行时 | 企业数据和工作流控制较弱；产品仍在预览 |
| Anthropic | 模型、Agent 工具、MCP 影响力和伙伴渠道 | 依赖伙伴实施；开放协议价值未必由自身捕获 |

## Potential beneficiaries and disadvantaged companies

### 可能受益的能力

- 控制企业数据、身份、权限和审计。
- 深度嵌入核心工作流。
- 拥有大规模企业分发。
- 能够衡量任务结果和 Agent ROI。
- 兼容开放协议，同时保留高价值上下文。

### 可能承压的能力

- 主要价值来自界面导航。
- 产品高度依赖人工席位但缺乏独特数据和工作流。
- 无法支持跨系统工具调用。
- Agent 成本高、结果难以验证。
- 产品发布多但缺乏生产采用和商业指标。

当前证据不足以把上述能力直接映射为股票买卖判断。

## Contrarian view

1. Agent 可能长期只是辅助界面，关键操作仍由人通过传统应用完成。
2. 企业安全、责任和变更管理可能显著放慢自主执行。
3. 开放协议可能使多个平台共存，而不是形成单一控制层。
4. 现有厂商可以把 Agent 打包进原有产品，避免收入被替代。
5. 当前 Agent 收入可能主要来自试点、打包和存量客户扩展，未必形成独立利润池。
6. 技术方向正确不代表当前估值提供投资回报。

## Falsification conditions

当前核心判断将被削弱，如果未来出现：

- Agent 生产使用和留存持续偏低。
- 核心工作流仍需要完整传统界面操作。
- 客户拒绝按用量或任务计价。
- 数据、权限和工作流被标准化到无法形成差异。
- Agent 平台无法跨应用执行或企业坚持应用内封闭 Agent。
- Agent 收入增长伴随更大席位流失、推理成本或服务成本，导致利润恶化。

## Key indicators

### 采用

- 生产账户绝对数。
- 周/月活跃 Agent 用户。
- 任务完成率和人工介入率。
- 从试点进入生产的比例。

### 商业化

- Agent ARR、ACV 和净新增合同。
- 任务/用量收入占比。
- Agent 毛利率和推理成本。
- Agent 收入与传统席位收入的替代关系。

### 控制权

- 谁控制用户入口。
- 谁控制身份、权限和审计。
- 谁控制跨系统工具和工作流。
- MCP/A2A 等开放协议的生产采用。

## Investment implications

当前只能形成研究优先级：

1. **优先研究有商业指标且拥有企业上下文的平台：** Salesforce、ServiceNow。
2. **优先验证产品架构能否转化为采用：** Oracle、SAP、Palantir。
3. **持续跟踪模型厂商是否越过应用层：** OpenAI、Anthropic。
4. **单独拆分 AI 基础设施与企业 Agent 收入：** Microsoft、Oracle。

进入 Investment Candidate 前仍需补齐：

- 市场预期与估值。
- 独立客户证据。
- 单位经济性。
- Agent 对存量收入的替代效应。

## Risks and unknowns

- 15 张 Event 与本报告综合判断均已获人工审核；尚未执行表中单独列出的 Thesis 置信度调整建议。
- 多数采用与效果指标来自公司自述。
- 缺少统一 Agent 指标定义。
- 缺少客户独立披露和续费数据。
- 缺少估值与市场共识分析。
- Palantir 10-Q 尚未完成逐页事实抽取。
- Microsoft Copilot 仅注册了促销定价线索，未形成完整价目表。

## Next research actions

1. 核验 Salesforce 和 ServiceNow 指标定义及绝对基数。
2. 补 Microsoft Copilot/Agent 正式价目表和电话会。
3. 抽取 Palantir Q1 2026 10-Q。
4. 获取至少四个独立客户案例。
5. 建立各公司 Agent 定价比较表。
6. 增加估值和市场预期模块。
7. 设定首次复盘日期。

## Sources

本报告使用 20 个 Source 中与 15 张 Event Card 关联的官方或高质量来源。具体映射见每张 Event Card 的 `source_ids`。

披露：Event 中使用的具体主张已经随 15 张 Event Card 完成人工审核；20 个完整 Source 记录的 Source 级 provenance、摘要和限制审核仍在独立队列中，因此当前保留 18 个 `REV003` 治理 warning。

## Review record

- Review date: 2026-07-29
- Reviewer: max
- Decision: approve
- Scope: 事实与推断边界、Evidence 可追溯性、反方观点、未知事项和可证伪条件
