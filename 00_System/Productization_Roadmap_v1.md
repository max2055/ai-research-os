# AI Research OS 中期产品化路线图 v1

版本：v1.0  
制定日期：2026-07-29  
目标版本：AI Research OS v0.2 Productized Local  
建议周期：7～8 周  
工作方式：Codex 实施、研究者决定、每个里程碑独立验收

## 1. 决策摘要

当前系统已经完成首轮 Research OS 建设，但仍是围绕 PRJ-001 构建的工程 MVP。下一阶段不再继续增加孤立脚本，而是直接建设一个：

> local-first、单用户优先、多项目可扩展、证据可追溯、默认人工审核的研究产品。

P0/P1 问题不单独形成长期路线，而是压缩为产品化工程的第一个稳定化门槛。稳定化完成后立即进入模块化内核、多项目、采集、通用审核、报告生成、Dashboard 和持续运行。

## 2. 产品化 v1 的完成定义

当以下完整路径无需修改代码即可运行时，v1 才算完成：

```text
创建研究项目
→ 捕获 URL / PDF / 本地资料
→ 保存可验证原文与哈希
→ 注册 Source
→ 生成 Event draft
→ 人工审核 Source / Event
→ 关联 Thesis 与 Company
→ 生成增量 Report draft
→ 人工审核 Report
→ Dashboard 展示状态、证据、行动与变化
→ Weekly / Monthly Review
```

系统必须同时满足：

- Markdown 仍为事实源。
- 所有研究判断仍需人工审核。
- 新项目无需复制或修改阶段 3 专用代码。
- Source、Event、Thesis、Company、Report、Review 和 Action 均可统一管理。
- 原始材料可长期复核，不只保留网页 URL。
- 任意派生索引和 Dashboard 数据均可重建。
- 自动化失败不会留下半写入对象。
- 项目状态、对象状态和正文状态不存在静默漂移。

## 3. 产品边界

### 3.1 v1 必须完成

- 可安装的 Python package 和稳定 CLI。
- 正式 Schema、迁移与生命周期服务。
- 通用审核系统。
- 多项目作用域。
- Source 原文归档、哈希、版本和去重。
- 可扩展采集 Adapter。
- Event draft 和 Report draft 工作流。
- 增量周报与快照比较。
- Action、复盘日期、逾期和 stale 检测。
- 本地只读 Dashboard。
- Git、CI、测试、迁移与恢复文档。
- 第二个研究项目的真实试运行。

### 3.2 v1 明确不做

- 自动股票买卖或投资组合执行。
- 多租户 SaaS、计费和公网部署。
- 实时多人协同编辑。
- 自动批准 Source、Evidence、Thesis 或 Report。
- 默认启用向量数据库。
- 默认启用常驻 SQLite 或图数据库。
- 无边界抓取全网新闻。
- 在缺少 Source 时由模型补写事实。

### 3.3 延后触发

- Event ≥ 500、Source ≥ 1,000 或多项目查询出现明确瓶颈后，再评估常驻 SQLite。
- Ontology 关系稳定两个复盘周期且高频三跳查询成为需求后，再评估图数据库。
- 只有 Obsidian 与本地 Dashboard 无法满足协作时，才评估 Web 编辑器与服务端。

## 4. 目标用户与核心任务

### 4.1 首要用户

个人 AI 产业研究者，使用本地文件、Obsidian 和 Codex，要求：

- 证据可回溯。
- 判断可复盘。
- 数据不被锁入云端产品。
- AI 能降低整理成本，但不能替代研究判断。

### 4.2 核心任务

1. 五分钟内建立新研究项目。
2. 一分钟内捕获一个 URL 或本地文件并生成 Source draft。
3. 从 Source 生成结构完整且可校验的 Event draft。
4. 在统一 Review Queue 中处理所有对象。
5. 查看每个 Thesis 的支持、反面、来源独立性和变化历史。
6. 自动生成“上次快照之后发生了什么”的周报草稿。
7. 查看逾期行动、复盘日期和 stale 对象。
8. 从 Company 或 Thesis 追踪一至多跳影响关系。
9. 从 Git 和 Markdown 完整恢复系统。

## 5. 产品化架构

## 5.1 分层结构

```text
src/research_os/
├── domain/
│   ├── models.py
│   ├── ids.py
│   ├── lifecycle.py
│   ├── relationships.py
│   └── policies.py
├── schemas/
│   ├── common.py
│   ├── source.py
│   ├── event.py
│   ├── thesis.py
│   ├── company.py
│   ├── report.py
│   ├── project.py
│   ├── review.py
│   └── action.py
├── repositories/
│   ├── markdown.py
│   ├── assets.py
│   ├── snapshots.py
│   └── derived.py
├── services/
│   ├── validation.py
│   ├── migration.py
│   ├── ingestion.py
│   ├── deduplication.py
│   ├── review.py
│   ├── synthesis.py
│   ├── reporting.py
│   ├── metrics.py
│   └── ontology.py
├── adapters/
│   ├── url.py
│   ├── file.py
│   ├── rss.py
│   ├── github.py
│   ├── arxiv.py
│   └── sec.py
├── cli/
├── api/
└── ui/
```

现有 `research_os.py` 保留为兼容入口，但核心逻辑迁入 package。

## 5.2 数据事实源

- Markdown front matter 和正文：研究事实源。
- `01_Inbox/_assets/<SOURCE_ID>/`：原始 HTML、PDF、文本、截图和元数据。
- Git：版本历史和恢复。
- JSONL、SQLite、Dashboard cache：可删除、可重建派生物。
- 指标快照：不可覆盖的历史观测。

## 5.3 建议技术选择

- Python 3.12+。
- `pyproject.toml` 管理 package、CLI 和测试依赖。
- Pydantic v2 定义对象 Schema。
- `ruamel.yaml` 读写 front matter，保留顺序、注释和人工格式。
- Typer 或 argparse 构建稳定 CLI；优先 Typer 以改善子命令和帮助。
- pytest 作为测试框架。
- Ruff 负责 lint 和 format。
- mypy 或 pyright 负责核心 domain/service 类型检查。
- FastAPI + HTMX 构建本地只读 Dashboard。
- SQLite FTS 仅作为可选派生搜索缓存，不成为事实源。

引入依赖前必须建立 Rule Change Proposal，并由研究者批准 Schema 与运行方式变化。

## 5.4 新增领域对象

### Project

```yaml
id: PRJ-NNN
type: project
status:
owner:
research_question:
charter_path:
review_cadence:
next_review_date:
```

### Review Decision

```yaml
id: REV-YYYYMMDD-NNN
type: review
target_ids: []
decision: approve|edit|reject
reviewer:
reviewed_at:
notes:
```

### Action

```yaml
id: ACT-YYYYMMDD-NNN
type: action
project_ids: []
owner:
due_date:
status: open|in_progress|done|cancelled
success_evidence:
source_review_id:
```

### Common field additions

建议通过正式迁移增加：

```yaml
schema_version:
project_ids: []
```

Source 建议增加：

```yaml
canonical_url:
asset_paths: []
content_sha256:
fetched_at:
upstream_source_ids: []
processing_status:
```

Report 建议增加：

```yaml
version:
supersedes:
superseded_by:
```

## 6. 目标 CLI

```text
research-os doctor
research-os project create|list|status
research-os source add|fetch|process|review
research-os event draft|review
research-os thesis status|review
research-os company status|review
research-os report draft|weekly|diff|review
research-os review queue|create|apply
research-os actions list|overdue|close
research-os metrics show|snapshot|compare
research-os index check|apply
research-os impact
research-os ui
```

现有命令保留至少一个版本周期的兼容：

- `validate`
- `status`
- `new-source`
- `new-event`
- `new-report`
- `metrics`
- `export`
- `scale`

## 7. 里程碑路线

## M0：稳定化门槛

周期：第 1 周前 2～3 天  
目标：消除会污染后续架构的已知正确性问题。

### 任务

| ID | 任务 | 依赖 | 交付 | 验收 |
|---|---|---|---|---|
| M0-01 | 修复 `new-event` 与 `EVT005` 冲突 | 无 | 生成器与回归测试 | 带 Thesis link 的 Event 创建后立即通过 validate |
| M0-02 | 修复 Report、Queue、Source Processing 状态漂移 | 无 | 状态同步与语义检查 | final/reviewed 不再出现“待审核”；已转化 Source 状态一致 |
| M0-03 | 明确 Source review 与 Event review 语义 | M0-02 | Rule Change Proposal | reviewed Event 引用 pending Source 的规则有唯一解释 |
| M0-04 | 建立 Git 私有仓库、`.gitignore` 和恢复说明 | 无 | 首个基线提交 | 可以从干净 clone 恢复并通过全部测试 |
| M0-05 | 增加 CLI 真实路径回归测试 | M0-01 | subprocess tests | new-source/event/report dry-run 与 apply 均有覆盖 |
| M0-06 | 清理 Stage Design 与 Acceptance 状态语义 | 无 | 文档一致性 | 不再同时存在未勾设计清单和已完成验收造成误读 |

### Gate M0

- 0 validation error。
- 0 index drift。
- P0 临时复现用例转为永久测试。
- 所有已知状态漂移归零。
- Git 恢复演练通过。

M0 不等待所有 Source 或 Company 审核完成；这些工作进入产品化并行研究流。

实施状态：`completed`（2026-07-29）。验收记录见
`00_System/M0_Productization_Acceptance.md`。

## M1：模块化内核与正式 Schema

周期：第 1～2 周  
目标：把单体脚本变成可维护、可测试、可扩展的产品内核。

### 任务

| ID | 任务 | 依赖 | 交付 | 验收 |
|---|---|---|---|---|
| M1-01 | 建立 `pyproject.toml` 与 `src/` package | M0 | 可安装 package | `pipx install -e .` 后可运行 `research-os doctor` |
| M1-02 | 拆分 1,939 行 core 模块 | M1-01 | domain/repository/service 分层 | 单文件不再承载多个业务域 |
| M1-03 | 引入 Pydantic 与 round-trip YAML | RCP 批准 | 正式 Schema | 现有 49 对象无损读取与写回 |
| M1-04 | 建立生命周期状态机 | M1-03 | lifecycle service | 非法状态迁移被拒绝 |
| M1-05 | 建立事务式写入与回滚 | M1-02 | write transaction | 多文件操作失败不留下半成品 |
| M1-06 | 建立 Migration Framework | M1-03 | dry-run/apply/rollback | 迁移幂等，有备份和变更清单 |
| M1-07 | 保持旧 CLI 兼容 | M1-01 | compatibility layer | 现有运行手册命令继续工作 |
| M1-08 | 建立 lint、type check、CI | M0-04 | CI workflow | test/lint/type/validate/index 全绿 |

### Gate M1

- 49 个现有对象迁移前后语义和内容哈希受控。
- 所有人工正文、注释和 Review history 保留。
- 核心测试覆盖率目标 ≥ 80%。
- CLI 行为有 golden tests。
- CI 在干净环境通过。

实施状态：`completed`（2026-07-29）。验收记录见
`00_System/M1_Productization_Acceptance.md`。

## M2：多项目与通用审核

周期：第 2～3 周  
目标：删除 PRJ-001 和 Stage 3 的硬编码，使第二个项目无需复制流程。

### 任务

| ID | 任务 | 依赖 | 交付 | 验收 |
|---|---|---|---|---|
| M2-01 | Project Registry 升级为结构化对象 | M1 | Project Schema | PRJ-001 可由 CLI 查询 |
| M2-02 | 为核心对象增加 `project_ids` | M1-06 | Schema migration | 跨项目 Source/Event 可复用 |
| M2-03 | 通用 Review Decision 对象 | M1-04 | Review Schema | 审核记录追加而非散落在正文 |
| M2-04 | 通用 Review Queue | M2-03 | `review queue` | 可按项目、类型、状态筛选 |
| M2-05 | 通用审核 apply | M2-03 | `review apply` | Source/Event/Thesis/Company/Report 均支持 |
| M2-06 | Action Register 结构化 | M1-03 | Action Schema | 可查询 overdue、owner、project |
| M2-07 | 项目级 status/metrics/index | M2-02 | project filters | PRJ-001 与全局统计可分别重算 |
| M2-08 | 删除阶段 3 专用审核硬编码 | M2-05 | compatibility wrapper | 旧审阅包仍可导入 |

### Gate M2

- 使用 CLI 创建 PRJ-002。
- PRJ-002 能独立拥有 Source、Event、Review、Action、Metrics 和 Report。
- PRJ-001 的结果不发生语义变化。
- 跨项目对象不会被重复创建。

实施状态：`completed`（2026-07-29）。验收记录见
`00_System/M2_Productization_Acceptance.md`。

## M3：Source 采集、原文归档与溯源

周期：第 3～4 周  
目标：从“保存链接”升级为“保存可复核研究材料”。

### 任务

| ID | 任务 | 依赖 | 交付 | 验收 |
|---|---|---|---|---|
| M3-01 | 设计 Source asset store | M1 | `_assets/<SRC-ID>` | HTML/PDF/Text/metadata 可统一保存 |
| M3-02 | URL fetch adapter | M3-01 | URL capture | 保留 canonical URL、时间、HTTP metadata 和哈希 |
| M3-03 | Local file adapter | M3-01 | file capture | 文件复制或引用策略明确 |
| M3-04 | 内容 SHA-256 与版本管理 | M3-01 | provenance | 网页变化不会静默覆盖旧版本 |
| M3-05 | canonical URL 与内容去重 | M3-02 | dedup service | 重复链接和相同正文被识别 |
| M3-06 | Published date 提取与人工确认 | M3-02 | date proposal | unknown 不被模型静默猜测 |
| M3-07 | Source processing state | M2-03 | state machine | captured/registered/extracted/reviewed 可查询 |
| M3-08 | RSS Adapter | M3-02 | bounded feed ingest | 仅抓明确 allowlist 来源 |
| M3-09 | GitHub Release Adapter | M3-02 | release ingest | 记录 repo、tag、发布时间和 release URL |
| M3-10 | arXiv / SEC Adapter 接口 | M3-02 | adapter contract | 可按项目启用，不默认全量抓取 |

### 首批 allowlist

- 公司 Investor Relations 与监管申报。
- OpenAI、Anthropic、Google、Meta 官方博客与发布页。
- GitHub 明确关注的项目 release。
- arXiv 明确 query，而非整个分类。
- SEC 明确公司 CIK 与表单类型。

### Gate M3

- 新 Source 至少 95% 有本地可复核资产或明确不可归档原因。
- 100% 有 canonical URL 或 local path。
- 100% 有内容哈希。
- 同一内容重复注册率接近 0。
- 网络失败、页面变化和 PDF 解析失败有明确状态。
- 不违反 robots、使用条款或访问频率限制。

实施状态：`completed`（2026-07-29）。验收记录见
`00_System/M3_Productization_Acceptance.md`。

## M4：研究工作流与智能生成

周期：第 4～5 周  
目标：自动化不再只生成 TODO 模板，而是生成可审阅的研究草稿。

### 任务

| ID | 任务 | 依赖 | 交付 | 验收 |
|---|---|---|---|---|
| M4-01 | Source→Event pipeline | M3, M2 | Event draft service | Facts/Inferences/Judgment 严格分区 |
| M4-02 | 引用片段与 Source anchor | M3 | citation anchors | 每个关键 Fact 可定位原文 |
| M4-03 | Thesis relationship proposal | M4-01 | impact rows | supporting/contradicting/contextual 完整生成 |
| M4-04 | 反面与替代解释检查 | M4-01 | quality gate | 缺失时不能进入人工审核 |
| M4-05 | 来源独立性检测 | M3-05 | upstream graph | 同一新闻稿转载不重复计证据 |
| M4-06 | reviewed Evidence→Report synthesis | M2 | report service | 不再只输出 TODO 骨架 |
| M4-07 | 增量 Weekly Report | metrics snapshots | report diff | 只报告上个快照后变化 |
| M4-08 | Report 版本与 supersession | M1-04 | lifecycle | v0.2 不覆盖 v0.1 |
| M4-09 | 公司画像增量更新提议 | M2 | knowledge proposal | 只用 reviewed Evidence |
| M4-10 | Human decision gate | M2-05 | review integration | 模型不能自行 final/reviewed |

### Gate M4

- 真实抽取 10 个新 Source，人工检查 Fact 准确率。
- 每个 Event 有 Source anchor、alternative explanation 和 unknowns。
- 所有 Thesis links 与 impact 表一致。
- Report 自动保留反面 Evidence。
- 重复运行不会重复创建 Event。
- AI 失败只能产生 pending 或 failed 状态。

实施状态：`engineering_completed / field_gate_pending`（2026-07-29）。工程验收见
`00_System/M4_Engineering_Acceptance.md`；真实 10-Source 人审见
`05_Research/Reviews/M4_Field_Review_Packet.md`。

## M5：Dashboard、Action 与持续运行

周期：第 5～6 周  
目标：减少依赖记住命令和手工浏览目录。

### 任务

| ID | 任务 | 依赖 | 交付 | 验收 |
|---|---|---|---|---|
| M5-01 | 本地 Dashboard shell | M1, M2 | FastAPI + HTMX | `research-os ui` 启动 |
| M5-02 | Project overview | M2 | 项目首页 | 显示问题、Thesis、Report、Actions |
| M5-03 | Review Queue | M2 | 审核视图 | 按项目和对象类型筛选 |
| M5-04 | Thesis health | M4 | Thesis 页面 | 正反 Evidence、置信度、历史、stale |
| M5-05 | Source provenance | M3 | Source 页面 | 原文、版本、哈希、引用 Event |
| M5-06 | Company / impact view | Ontology | 关系页面 | 一至多跳可解释 |
| M5-07 | Metrics and snapshot diff | Stage 5 | 趋势页 | 展示变化而非只有当前值 |
| M5-08 | Action overdue 与 review due | M2-06 | 运营页 | 逾期、即将到期、owner |
| M5-09 | Obsidian Home Dashboard | M2 | Markdown/Dataview | 无 Web 服务时仍可查看 |
| M5-10 | Scheduler entrypoints | M3, M4 | jobs CLI | OS scheduler 可调用，任务幂等 |

### Dashboard v1 边界

- 默认只读。
- 审核决定可先跳转 CLI 或生成 review packet。
- 不直接编辑事实正文。
- 不开放公网。
- 不引入用户账户和权限系统。

### Gate M5

- 从首页三次点击内到达任一 Source、Event、Thesis 或 Action。
- 所有页面数据都能从 Markdown 重建。
- Dashboard cache 删除后可以恢复。
- 无 stale 状态展示。
- 任务失败会出现在健康页。

实施状态：`completed`（2026-07-29）。验收记录见
`00_System/M5_Productization_Acceptance.md`。

## M6：第二项目试运行与 v0.2 发布

周期：第 6～8 周  
目标：用真实第二项目证明产品不是 PRJ-001 的定制脚本。

### 第二项目选择

建议选择与现有 Taxonomy 有重叠、但研究对象不同的主题，例如：

- AI Coding Agent 的价值链与商业化；
- AI 推理基础设施瓶颈；
- 企业 Agent 协议与控制层竞争。

避免同时选择过于宽泛的“整个 AI 行业”。

### 任务

| ID | 任务 | 依赖 | 交付 | 验收 |
|---|---|---|---|---|
| M6-01 | 创建 PRJ-002 Charter | M2 | 新项目 | 边界、Thesis、成功标准明确 |
| M6-02 | 采集 10～15 个 Source | M3 | Source set | 原文归档、去重、哈希完整 |
| M6-03 | 形成 8～10 个 Event | M4 | Event set | 全部完成人工审核 |
| M6-04 | 生成首篇 PRJ-002 Report | M4 | Report | 正反 Evidence 和 unknowns 完整 |
| M6-05 | 完成 Weekly + Monthly Review | M5 | Review records | Action 与指标变化闭环 |
| M6-06 | 性能基准 | M1 | benchmark | 合成 1,000 Source / 500 Event 仍可用 |
| M6-07 | 恢复演练 | M0-04 | recovery report | 新机器从 Git + assets 恢复 |
| M6-08 | 发布 v0.2 | 全部 | release notes | DoD 全部通过 |

### Gate M6

- PRJ-001 和 PRJ-002 可独立查询、审核、报告和复盘。
- 没有项目路径硬编码。
- 真实日常运行至少两个完整周度周期。
- 系统未自动批准任何研究判断。
- 用户能在不修改代码的情况下完成全闭环。

实施状态：`completed / v0.2.0 released`（2026-08-11）。
PRJ-002 的 12 个 Source、9 个 Event、首篇 Report、M4 人审、两次 Weekly、一次
Monthly、研究质量 Actions、性能与恢复 Gate 均已完成。v0.2 release check 为
18/18 Ready，max 于 2026-08-08 批准发布。release engineering 于 2026-08-11
完成：包版本 `0.2.0`、annotated tag `v0.2.0`、private GitHub Release、wheel、
sdist 与 SHA-256 manifest。

## 8. 并行研究质量流

以下 P1 工作从 M0 后与工程并行，不阻塞模块化开发，但必须在 v0.2 发布前关闭或有正式延期决定。

| ID | 研究行动 | 对应现有 Action | 目标 |
|---|---|---|---|
| RQ-01 | 审核 18 个已被 Event 使用的 Source | ACT-20260729-001 | Source/Event 治理一致 |
| RQ-02 | 获取 4 个独立客户案例 | ACT-20260729-002 | 降低官方材料依赖 |
| RQ-03 | 为 THS-001 找直接反证 | ACT-20260729-003 | 证据平衡 |
| RQ-04 | 为 THS-005 找直接反证 | ACT-20260729-004 | 证据平衡 |
| RQ-05 | 补 Microsoft 正式定价和电话会 | ACT-20260729-005 | 完整商业模式 |
| RQ-06 | 完成 Palantir 10-Q 抽取 | ACT-20260729-006 | 监管事实基线 |
| RQ-07 | 审核 8 个 Company Profile | ACT-20260730-001 | 公司知识权威化 |
| RQ-08 | 建立估值与市场预期模块 | ACT-20260730-002 | 从产业研究走向投资研究 |

## 9. 产品成功指标

## 9.1 正确性

- Validation error：持续为 0。
- Index drift：合并前为 0。
- 新对象创建后首次 validate 通过率：100%。
- reviewed Report 引用非 reviewed Evidence：0。
- 状态正文与 front matter 漂移：0。
- 永久 ID 冲突：0。

## 9.2 研究质量

- 关键 Fact 有 Source anchor：100%。
- Source 有本地资产或明确例外：≥ 95%。
- `published_at: unknown`：< 5%。
- reviewed Event 至少一个 Source：100%。
- 核心 Thesis 有直接反面 Evidence：100%，或有正式搜索无结果记录。
- 报告明确披露公司自述与独立证据：100%。

## 9.3 效率

- 创建项目：< 5 分钟。
- 捕获 URL 并形成 Source draft：< 1 分钟，不含人工审核。
- Source→Event draft：< 3 分钟。
- 生成增量周报草稿：< 2 分钟。
- 全量 validate + index：当前规模 < 5 秒。
- Review Queue 能在一个入口处理。

## 9.4 运营

- Weekly Review 按期完成率：≥ 90%。
- Monthly Review 按期完成率：100%。
- overdue Action 可见率：100%。
- failed ingestion 可见率：100%。
- Snapshot 连续性：无缺失月份。

## 10. 测试与发布策略

## 10.1 测试层级

1. Domain unit tests。
2. Schema round-trip golden tests。
3. Repository contract tests。
4. CLI subprocess tests。
5. Migration idempotency tests。
6. Adapter tests，网络使用固定 fixture。
7. End-to-end temporary vault tests。
8. PRJ-001 regression tests。
9. PRJ-002 real workflow acceptance。
10. Synthetic scale tests。

## 10.2 每次合并闸门

```text
format
→ lint
→ type check
→ unit/integration tests
→ research-os doctor
→ validate
→ index --check
→ migration dry-run
```

## 10.3 发布内容

- Git tag。
- Release notes。
- Schema version。
- Migration guide。
- Backup/restore guide。
- Known limitations。
- Test and validation report。
- Product metrics baseline。

## 11. 安全、隐私与合规

- API key 不写入 Vault、Markdown 或 Git。
- 使用 macOS Keychain、环境变量或本地 secrets store。
- `_assets` 是否进入 Git 由版权、体积和隐私策略决定。
- 公开网页归档遵守 robots、条款和频率限制。
- SEC、arXiv、GitHub 和 RSS Adapter 使用明确 User-Agent 与 rate limit。
- 不自动上传私有研究材料。
- LLM 输入范围必须可见、可限制。
- Dashboard 默认仅监听 localhost。
- 删除操作默认移动到可恢复位置。

## 12. 主要风险与控制

| 风险 | 表现 | 控制 |
|---|---|---|
| 过早做 UI | 页面很多但工作流仍不稳定 | M0～M4 Gate 未通过前不扩展编辑 UI |
| Schema 频繁变化 | 迁移成本和数据漂移 | Schema version、RCP、幂等 migration |
| AI 草稿被误当事实 | 报告质量下降 | pending 默认、Source anchor、Human gate |
| 官方来源偏差 | 高等级但不独立 | upstream、独立性指标、客户案例配额 |
| 采集失控 | 噪音和重复内容增加 | allowlist、项目 query、配额、去重 |
| iCloud 与 Git 冲突 | 文件重复或合并错误 | 单一工作目录、Git 规则、冲突检查 |
| 单体代码再次增长 | 修改风险上升 | domain/service/adapters 分层与模块所有权 |
| 第二项目污染 PRJ-001 | 指标和对象混杂 | project_ids、项目过滤、回归测试 |
| Dashboard 成为第二事实源 | UI 与 Markdown 不一致 | 只读、可重建 cache、无直接 DB 写入 |

## 13. 关键路径与并行关系

```text
M0 Stabilization
      ↓
M1 Modular Core
      ↓
M2 Multi-project + Generic Review
      ↓
M3 Ingestion + Provenance ─────┐
      ↓                        │
M4 Research Automation ◀───────┘
      ↓
M5 Dashboard + Operations
      ↓
M6 PRJ-002 Pilot + v0.2
```

并行流：

- RQ-01～RQ-08 从 M0 后持续进行。
- Dashboard 视觉设计可在 M3 开始，但实现不应早于 M2 数据接口稳定。
- Adapter 可以并行开发，但必须共享同一个 capture contract。

## 14. 建议日历

| 周 | 主里程碑 | 人工决策点 |
|---|---|---|
| 第 1 周 | M0 + M1 启动 | Source review 语义、依赖与 Schema RCP |
| 第 2 周 | M1 完成 + M2 启动 | Project/Review/Action Schema |
| 第 3 周 | M2 完成 + M3 启动 | 首批采集 allowlist |
| 第 4 周 | M3 完成 + M4 启动 | AI 草稿质量阈值 |
| 第 5 周 | M4 完成 | Report 版本与审核策略 |
| 第 6 周 | M5 | Dashboard 是否保持只读 |
| 第 7 周 | M6 PRJ-002 | 第二主题 Charter 和 Thesis |
| 第 8 周 | Pilot、恢复演练、v0.2 | 发布决定 |

如果每周投入时间有限，保持里程碑顺序不变，将周期延长到 10～12 周，不应通过跳过 Gate 缩短周期。

## 15. 立即执行顺序

第一批任务建议按以下顺序开始：

1. M0-01：修复 `new-event`/`EVT005`。
2. M0-02：修复状态漂移并增加语义校验。
3. M0-04：建立 Git 与恢复基线。
4. M0-03：提交 Source review 语义 RCP。
5. M1-01：建立 package 与 `pyproject.toml`。
6. M1-02：拆分 core。
7. M1-03：Schema round-trip 原型和迁移 dry-run。
8. M2-03：通用 Review Decision。
9. M2-01/M2-02：Project 与 `project_ids`。
10. M3-01：Source asset store 原型。

在 M0 Gate 通过后，不再单独为其他 P1 问题停留；研究质量工作与产品化工程并行推进。

## 16. 最终验收清单

- [x] M0～M6 Gate 全部通过。
- [x] PRJ-001 完整回归通过。
- [x] PRJ-002 完成真实闭环。
- [x] 通用审核覆盖全部对象类型。
- [x] 原始 Source 可长期复核。
- [x] Event 和 Report 自动化不再只生成 TODO。
- [x] Dashboard、Actions、Metrics、Review cadence 连成日常工作流。
- [x] Git、CI、迁移和恢复演练通过。
- [x] 没有自动批准研究判断。
- [x] Markdown 仍为唯一事实源。
- [x] 当前规模下没有无必要的常驻数据库或图数据库。
- [x] v0.2 Release notes、Known limitations 和下一阶段决策完成。

上述清单与 `v0.2.0` 发布均已完成；v0.3 仍使用独立 Release Gate。
