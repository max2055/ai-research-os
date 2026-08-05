# PRJ-002 Research Charter：AI Coding Agent 的价值链与商业化

版本：v0.1  
状态：Active pilot  
建立日期：2026-07-29  
Owner：max

## 1. Research question

AI Coding Agent 正在把软件开发价值从模型与 IDE 重新分配到哪些环节，哪些商业模式
和护城河假设值得用可复核证据持续验证？

## 2. Purpose

本项目同时服务两个目标：

1. 形成一个边界明确、可证伪的 AI Coding Agent 产业研究闭环。
2. 验证 AI Research OS 的 Project、Source、Event、Review、Report、Dashboard 和
   Scheduler 能否在不复制 PRJ-001 代码的情况下运行第二主题。

项目不预设任何公司或证券的投资结论。

## 3. Scope

纳入：

- 通用与专业 AI Coding Agent。
- IDE、CLI、云端异步 Agent、代码审查和软件工程任务执行。
- 模型、repository context、sandbox、toolchain、evaluation、distribution。
- 个人开发者、团队和企业的采用、定价、单位经济性和治理。
- 产品文档、release、定价、客户案例、经营披露和独立评测。

排除：

- 所有通用开发工具的穷举。
- 仅有代码补全、没有 Agent task execution 的历史产品比较。
- 未经核验的排行榜或社交媒体使用数据。
- 自动股票推荐、交易和估值结论。

## 4. Value-chain model

```text
基础模型与推理
→ Coding Agent runtime / planning
→ repository context / memory / evaluation
→ sandbox / CI / tools / deployment
→ IDE / CLI / cloud task entry
→ developer team and enterprise governance
→ software delivery outcome
```

## 5. Pending Thesis

- `THS-006`：任务入口可能从交互式 IDE 部分迁移到异步 Agent task layer。
- `THS-007`：repository context、evaluation、sandbox 和 workflow integration
  可能比单一模型选择更持久。
- `THS-008`：商业模式可能从 seat 扩展到 usage/task，但推理与验证成本限制利润池。

这些 Thesis 均为 pending 假设，不能在没有 reviewed Evidence 时提升置信度。

## 6. Initial entity set

首轮只建立候选清单，不把公司声明当事实：

- GitHub Copilot；
- Cursor / Anysphere；
- Anthropic Claude Code；
- OpenAI Codex；
- Google Gemini Code Assist / coding agents；
- 具有可复核产品、定价、客户或经营证据的其他候选。

正式公司/Product 对象只在 Source 进入后按去重规则创建。

## 7. Evidence plan

首轮目标 10～15 个新 Source：

- 至少 6 个 A 级：正式文档、定价、release、财务或监管材料。
- 至少 2 个独立客户/团队采用来源。
- 至少 2 个可复核方法的独立评测或技术研究。
- 支持与反面材料都必须进入。
- 100% 通过 M3 capture 保存本地资产、hash 与 provenance。

Discovery 只使用明确 GitHub repository、官方 RSS/URL、arXiv query 或公司材料；
不得全网无边界抓取。

## 8. Success criteria

- 10～15 个 archived/processed Source，重复内容率接近 0。
- 8～10 个带 Fact anchor 的 pending Event。
- 10 个 Source→Event 进入 M4 人工准确率验收包。
- 每个 Thesis 至少一项 supporting 和一项 contradicting Evidence，或有正式无结果记录。
- 所有 Event 完成人工 Review Decision。
- 形成一篇包含正反 Evidence、unknowns 和 falsification 的 reviewed Report。
- 完成两个真实 Weekly cycle 和一个 Monthly review。
- PRJ-001 与 PRJ-002 status、metrics、indexes、Dashboard 和 reports 可独立查询。

## 9. Falsification and stop conditions

应削弱或终止相关假设，如果：

- Agent task completion 长期无法达到生产可靠性。
- 开发团队不把异步 Agent 用于真实工程任务。
- repository context/evaluation 被快速标准化且不形成差异。
- usage/task 收入无法覆盖推理、验证和支持成本。
- 企业治理要求使 Agent 只能保留为低价值辅助功能。

项目暂停条件：

- 连续两轮找不到 A/B 级新证据。
- Source 许可不允许本地复核且无合法替代。
- 研究范围开始扩展为“所有开发工具”。

## 10. Review cadence

- Weekly：每周三，首轮 2026-08-05。
- Monthly：首轮 2026-08-29。
- 每轮必须记录 system facts、Evidence change、conflicts、decisions 和 Action。
- 自动化只能生成 review packet，不得填写人类 decision。
