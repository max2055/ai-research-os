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

阶段 0～6 已完成首轮建设，产品化 M0～M5 与 10-Source 真实人审 Gate 已通过；
当前正在执行 v0.2 的 M6 第二项目真实试点与发布准备，并推进已批准的 v0.3
工程工作包。Markdown 仍是唯一研究事实源。

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

自动化入口：

```bash
python3 09_Automation/research_os.py status
python3 09_Automation/research_os.py validate
python3 09_Automation/research_os.py index --check
```

产品化安装与诊断：

```bash
python3 -m venv /tmp/ai-research-os-dev-venv
/tmp/ai-research-os-dev-venv/bin/pip install -e ".[dev,ui]"
/tmp/ai-research-os-dev-venv/bin/research-os doctor
source /tmp/ai-research-os-dev-venv/bin/activate
```

启动本地只读 Dashboard：

```bash
research-os ui
```

默认地址为 `http://127.0.0.1:8765`，v1 只允许 loopback，不提供 Web 写入。

本地完整校验必须使用 strict 模式；它会读取 Git 外的真实 Source assets：

```bash
research-os validate --strict
research-os index --check
research-os index --check --project PRJ-001
research-os index --check --project PRJ-002
```

私有 GitHub CI 因不接触 raw assets、Candidate DB 或 secrets，只运行显式的
metadata-only 子集：

```bash
research-os validate --metadata-only
research-os index --check --metadata-only
```

metadata-only 不能替代上述 strict local Gate。

查看发布状态：

```bash
research-os release check
research-os release check --version 0.3 --format json
```

默认命令保持 v0.2 的 18 Gate；显式 `--version 0.3` 运行 F-023 机器检查。
两者都只读。v0.3 当前仍由 WP-530、WP-620 和 F-024 独立阻断，自动化不能代填
真实 Source、Forecast outcome、Weekly/Monthly 运行或最终发布决定。

加密 durable backup 先 dry-run，再显式 apply：

```bash
BACKUP_CONFIG=09_Automation/operational/backup.local.json
research-os backup durable create --config "$BACKUP_CONFIG"
research-os backup durable create --config "$BACKUP_CONFIG" --apply
```

该命令将 Candidate SQLite snapshot 与 Source assets 分成两组，经 `age` 加密后上传到
配置的 private GitHub backup prerelease。密钥配置、24 小时 RPO、remote verify 与
disposable restore 步骤见 `00_System/Recovery_Runbook.md`。

激活产品环境后，旧的 `python3 09_Automation/research_os.py ...` 入口
至少保留一个版本周期；兼容入口不再包含独立的无依赖业务内核。
仓库位于 iCloud 时，开发 venv 应放在同步目录外。

首轮建设完成审计见：`00_System/Implementation_Audit.md`。

中期产品化路线图见：`00_System/Productization_Roadmap_v1.md`。

面向 AI 全产业 Universe、每日情报、跨板块 Ontology、Analysis Mode、Forecast 与
投资决策支持的 v0.3 扩展已批准进入分阶段实施，规划与执行状态见：

- `00_System/v0.3_AI_Industry_Intelligence_OS/00_Master_Roadmap.md`

该规划不静默改变 Research Rules、Taxonomy、Schema 或人工审核边界；相关 Rule
Change Proposal 均按各阶段 Gate 留存人审决定与审计记录。

恢复与备份边界见：`00_System/Recovery_Runbook.md`。
