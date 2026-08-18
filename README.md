# AI Research OS

AI Research OS 是一套面向 AI 产业研究的个人研究操作系统。

它的目标不是聚合尽可能多的信息，也不是自动生成投资结论，而是建立一条可以持续运行和复盘的研究闭环：

```text
研究问题
→ 收集原始材料
→ 提取事实与事件
→ 关联研究假设
→ 形成产业判断
→ 推导投资含义
→ 持续跟踪与复盘
```

## 当前阶段

阶段 0～6 已完成首轮建设，产品化 M0～M6 与 10-Source 真实人审 Gate 已通过。
v0.2 的 18/18 Release Gate 和具名人工发布决定已于 2026-08-08 完成，v0.2.0
于 2026-08-11 以 `v0.2.0` Git tag 和 GitHub Release 发布。v0.3 工程主体与
operational-hardening MVP 已合并，F-023 当前 16/21 checks 通过，仍未获准
发布。Markdown 仍是唯一研究事实源。

当前状态读取顺序：

1. 网站 System Health / Release 页面；内部 release evaluator 提供机器 Gate。
2. 具名、带日期的人审文件：人工决定。
3. `00_System/v0.3_AI_Industry_Intelligence_OS/09_Master_Backlog.md`：执行状态。
4. README 与阶段路线图：摘要；带日期的 Audit/Acceptance 是时间点证据，不覆盖当前态。

当前研究主题：

> AI Agent 时代，企业软件价值链是否正在重构？

第二项目试点：

> AI Coding Agent 正在把软件开发价值重新分配到哪些环节？

阶段 0 的正式定义见：

- `00_System/Phase_0_Research_Charter.md`

研究方法内核见：

- `00_System/Research_Framework.md`
- `00_System/Taxonomy.md`
- `00_System/Research_Rules.md`
- `00_System/Source_Policy.md`

## 建设原则

1. 研究方法先于自动化。
2. 证据先于观点。
3. 明确区分事实、推断和判断。
4. 每个核心判断必须可以被证伪。
5. AI 负责扩展研究能力，不替代人的投资判断。
6. 先完成一个小闭环，再扩大信息源和研究范围。
7. 在 Markdown 无法满足查询需要前，不引入数据库或知识图谱。

## 路线图

1. 阶段 0：确定研究主题与成功标准。
2. 阶段 1：建立文件系统骨架。
3. 阶段 2：建立研究框架、分类体系和研究规则。
4. 阶段 3：完成人工研究闭环。
5. 阶段 4：实现 Codex 自动化流水线。
6. 阶段 5：建立反馈与复盘机制。
7. 阶段 6：按规模引入数据库与 Ontology。

## 当前建设状态

- [x] 阶段 0：研究主题、边界和成功标准。
- [x] 阶段 1：文件系统骨架和元数据。
- [x] 阶段 2：研究框架、分类体系和证据规则。
- [x] 阶段 3：首个人工研究闭环和权威化审核。
- [x] 阶段 4：Codex 自动化流水线。
- [x] 阶段 5：反馈与复盘机制。
- [x] 阶段 6：规模化和 Ontology 升级。

唯一产品入口：网站：

```bash
python -m research_os.ui
```

打开 `http://127.0.0.1:8765/home`。根据 RCP-v03-011，网站是唯一用户产品界面。
网站启动时会启动并监督唯一一个内置 Worker；网站停止时 Worker 同步停止，停机期间
不会执行定时任务。计划的创建、编辑、暂停、恢复和立即运行统一在
`/operations/schedules` 完成，运行历史和审计以
`09_Automation/operational/operations.db` 为权威。Channel Markdown 中的旧运行字段只在
首次切换时导入，之后不再用于运行时排期；已有 `JOB-*.md` 仅作为历史记录保留。

`/operations/jobs` 查看数据库运行记录，`/operations/backups` 发起 Candidate 或 durable
备份，`/health` 查看 Worker heartbeat、当前运行、计划状态和备份告警。网站 Worker
只能执行 operational Job，不能批准研究对象或修改 Thesis conclusion/confidence。

启动前会执行只读 Runtime preflight，拒绝 linked worktree、代码/数据根目录不一致、
未解决合并冲突和损坏的 Candidate/Operations 数据库。`/health` 显示 root、branch、
commit、dirty、interpreter、package path 和数据库路径；这些字段是确认当前运行版本的
第一入口。产品 CLI entry point 已移除，开发、CI 和灾备适配器不属于用户产品面。

当前 v0.3 发布状态仍由 `/health/release` 与具名人工决定共同控制。工程迁移完成不自动
通过真实 Pilot、自然 Resolution、cadence、Known Limitations 阅读确认或最终发布批准。

托管 CI 只运行不依赖本地原始资产的 metadata-only 检查；它不能替代网站 `/health` 中的
strict local 校验、真实 Source asset 检查或灾备恢复验收。开发、CI 与恢复所用的内部
maintenance adapter 不安装为产品命令，也不构成第二个用户入口。

Durable backup 从 `/operations/backups` 预览并确认。浏览器不接收配置路径、recipient
或 token；Worker 只读取固定的 ignored 服务端配置
`09_Automation/operational/durable_backup.json`。Candidate 加密集合同时包含 Candidate
SQLite snapshot、`operations.db` snapshot 及其 manifest，Source assets 仍为第二个加密
集合。密钥配置、24 小时 RPO、remote verify 与 disposable restore 步骤见
`00_System/Recovery_Runbook.md`。

定时任务、手动 Job、备份、恢复状态与健康检查统一通过网站操作页完成。
内部维护和恢复 adapter 不安装产品命令；Worker 子进程入口也是内部实现。
仓库位于 iCloud 时，开发 venv 应放在同步目录外。

首轮建设完成审计见：`00_System/Implementation_Audit.md`。

中期产品化路线图见：`00_System/Productization_Roadmap_v1.md`。

面向 AI 全产业 Universe、每日情报、跨板块 Ontology、Analysis Mode、Forecast 与
投资决策支持的 v0.3 扩展已批准进入分阶段实施，规划与执行状态见：

- `00_System/v0.3_AI_Industry_Intelligence_OS/00_Master_Roadmap.md`

该规划不静默改变 Research Rules、Taxonomy、Schema 或人工审核边界；相关 Rule
Change Proposal 均按各阶段 Gate 留存人审决定与审计记录。

恢复与备份边界见：`00_System/Recovery_Runbook.md`。
