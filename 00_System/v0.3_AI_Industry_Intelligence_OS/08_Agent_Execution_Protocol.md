# v0.3 Agent 执行与交接协议

状态：`active`（v0.3 执行工作包采用；2026-08-11 状态同步）
目的：让后续编码/研究 Agent 在缺少原始对话时仍能安全接手，并防止目标、规则和数据语义漂移。

## 1. Agent 开工必读顺序

每个工作包开始前，Agent 必须完整读取：

1. 根目录 `AGENTS.md`；
2. `README.md`；
3. `00_System/Research_Rules.md`；
4. `00_System/Source_Policy.md`；
5. `00_System/Research_Framework.md`；
6. `00_System/Workflow.md`；
7. `00_System/Metadata_Schema.md`；
8. 本目录 `00_Master_Roadmap.md`；
9. `01_Product_Charter_and_Governance.md`；
10. 当前阶段计划；
11. 与工作包相关的 RCP、模板、服务、测试和现有对象；
12. `07_Templates/Research_Handoff.md`。

不得让子 Agent 代替主实施 Agent 阅读和解释这些规则。

## 2. Work Package 输入合同

派发给 Agent 的任务必须包含：

```text
Work Package ID:
Objective:
In scope:
Out of scope:
Required reading:
Approved RCP IDs:
Owned files/directories:
Read-only neighboring files:
Dependencies/commits:
Required tests:
Field/human Gate:
Expected deliverables:
Stop conditions:
Handoff destination:
```

如果缺少 Approved RCP、永久 ID 语义、迁移策略或人工选择，Agent 只能完成 proposal、
spike 或 read-only audit，不得自行决定并写入生产 Schema。

## 3. 工作包大小与所有权

- 一个工作包建议 0.5–3 个工作日；
- 一个工作包只包含一个主要业务能力；
- Schema、migration、service、内部 maintenance adapter、tests、docs 可以属于同一个垂直工作包；
- 不要把整个 Phase 交给单个 Agent 一次完成；
- 同一时间同一文件只能有一个 owner；
- 同一正式对象、同一 Thesis confidence、同一 Taxonomy 文件、同一 migration 不并行修改；
- Adapter、UI 页面、独立 Schema tests 可以在接口稳定后并行；
- 并行工作必须在主 Backlog 登记 file ownership 和 integration owner。

## 4. 开工检查

```bash
git status --short --branch
git log -5 --oneline
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python 09_Automation/research_os.py doctor
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python 09_Automation/research_os.py validate
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python 09_Automation/research_os.py index --check
/Users/max/.venvs/ai-research-os/bin/pytest -q
```

记录 baseline commit、对象数、测试数、warnings 和已存在 worktree changes。

如果 worktree 不干净：

- 不得覆盖或 reset 用户修改；
- 判断是否与工作包重叠；
- 不重叠则保留并避开；
- 重叠且无法安全合并时停止并请求协调；
- 禁止 `git reset --hard`、`git checkout --` 等破坏性处理。

## 5. 实施顺序

建议每个垂直工作包按以下顺序：

1. 复现/定义行为；
2. 写 ADR/RCP 或确认已批准；
3. 定义 Schema/接口；
4. 增加失败和安全测试；
5. 实现 domain policy；
6. 实现 repository transaction；
7. 实现 service；
8. 接 CLI/API/UI；
9. migration dry-run；
10. fixture integration；
11. real repository read-only check；
12. 经批准后 apply；
13. validate/index/test；
14. 更新 runbook/known limitations；
15. 完成交接。

不要先做 UI，再反推不稳定的数据语义。

## 6. 工程约束

### Schema

- 使用 Pydantic；
- YAML round-trip 保留人工正文、顺序和注释；
- 新字段要有 compatibility/default/migration 决定；
- 枚举值有明确语义；
- ID 永久且全局唯一；
- 不通过猜测填充 unknown；
- 新正式对象必须进入 validation、count/index/ontology/recovery。

### Repository/Transaction

- 多文件写入使用现有 `FileTransaction` 或扩展后的事务；
- dry-run 不写文件；
- apply 原子或可回滚；
- 不覆盖已有永久对象；
- 不使用 Candidate DB 绕过 Markdown review；
- operational DB migration 有版本和备份；
- crash/failure 测试不能留下半状态。

### CLI

- `--help` 完整；
- 查询默认只读；
- mutation 默认 dry-run，显式 `--apply`；
- 错误信息可操作；
- 退出码稳定；
- legacy command 兼容至少一个版本周期，或有批准的 migration guide。

### UI/API

- Dashboard 默认 loopback-only、read-only；
- 外部内容 escape；
- 无任意路径读取；
- pagination/filter 有上限；
- read model 可重建；
- 不把 cache 当事实源；
- mutation 需要单独批准和 CSRF/auth 设计，v0.3 默认不做。

### AI/Model

- 模型只生成 structured proposal；
- 输入 manifest、model ID、prompt/version、参数和 hash 可追踪；
- 输出必须经过确定性 Schema/引用/必填检查；
- prompt injection 内容不能改变工具、规则或审批状态；
- 模型失败/超时不创建 completed 对象；
- 模型评分不得自动变成 Source grade、confidence 或 recommendation。

## 7. 测试矩阵

每个新能力至少考虑：

| 类别 | 必须覆盖 |
|---|---|
| Happy path | dry-run、apply、read-back、index/export |
| Schema | missing、wrong type、enum、date、ID、unknown |
| References | missing target、wrong type、cross-project、stale |
| Lifecycle | legal/illegal transition、review requirement |
| Idempotency | repeated run、same fingerprint、same snapshot |
| Transaction | mid-write failure、rollback、existing target |
| Compatibility | v0.2 object/CLI/read model |
| Security | path、HTML、secret、untrusted content、size/timeout |
| Failure | network、parse、model、DB lock/corruption、disk |
| Time | timezone、as-of、future leakage、stale、resolution due |
| Performance | stated scale fixture and p95 target |
| Recovery | export/snapshot/clean rebuild |

自动测试不能替代真实 Source、Impact、Mode、Forecast 人审 Gate。

## 8. 验证命令

工作包完成至少运行：

```bash
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python 09_Automation/research_os.py validate
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python 09_Automation/research_os.py index --check
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python 09_Automation/research_os.py index --check --project PRJ-001
PYTHONPATH=src /Users/max/.venvs/ai-research-os/bin/python 09_Automation/research_os.py index --check --project PRJ-002
/Users/max/.venvs/ai-research-os/bin/pytest --cov=research_os --cov-report=term-missing
/Users/max/.venvs/ai-research-os/bin/ruff check src 09_Automation/tests
/Users/max/.venvs/ai-research-os/bin/mypy src/research_os
git diff --check
git status --short
```

若工作包修改研究对象，先在批准后 `index --apply`，再检查 global/project drift。

## 9. Commit 与集成

- 一个逻辑工作包一个或少量原子 commit；
- commit message 包含 Work Package ID；
- 不混入无关格式化；
- 不提交 secret、Candidate DB 实例、受限 Source asset 或临时输出；
- migration 与对应 Schema/tests 同 commit 或明确依赖；
- integration owner 在合并后重新运行全部 Gate；
- 不以“我的测试通过”替代全仓库验证；
- 没有远程仓库时不要宣称 CI 通过，只能报告本地 clean-run。

## 10. 人工停止条件

遇到以下情况必须停止写入并请求决定：

- 需要修改 Research Rules、Source Policy 或 Taxonomy 含义；
- 新永久 ID/对象类型没有批准；
- Candidate 与 canonical Source 边界不明确；
- 数据许可或 robots 状态不明确；
- 需要绕过登录/付费墙；
- 要自动改变 Thesis confidence 或 Recommendation；
- 同一事实存在不可合并的来源冲突；
- migration 可能丢失人工正文或 Review history；
- 需要删除/覆盖 raw Source asset；
- 用户修改与工作包重叠；
- 性能方案需要改变事实源；
- 工作包范围必须扩大到另一个 Phase。

## 11. Agent Handoff 输出

除 `07_Templates/Research_Handoff.md` 字段外，工程交接必须包含：

```text
Work Package ID:
Baseline commit:
Final commit(s):
Approved RCP(s):
Files owned:
Files changed:
Schema/API/internal-adapter changes:
Migration and rollback:
Tests added:
Commands run and exact result:
Real-data actions performed:
Objects/IDs created:
Dry-run/apply distinction:
Known limitations:
Unresolved questions:
Human decisions still required:
Recommended next Work Package:
```

如果没有运行某项检查，写 `not run` 和原因，不能省略。

## 12. 给下一个 Agent 的标准任务 Prompt

```text
你正在 AI Research OS 仓库实施 Work Package <ID>。

目标：<objective>
范围：<in scope>
非范围：<out of scope>
批准的治理决定：<RCP IDs>
允许修改：<owned files>
只读参考：<neighboring files>
依赖 baseline：<commit / prior WP>

开工前必须完整读取 AGENTS.md、README、Research_Rules、Source_Policy、
Metadata_Schema、v0.3 Master Roadmap、Agent Execution Protocol 和当前阶段计划。

不要修改 Thesis confidence，不要批准生成对象，不要覆盖 raw Source，不要创建未经批准的
Schema/ID。mutation 默认 dry-run，明确要求时才 apply。

交付：<deliverables>
验收：<tests and gates>
停止条件：<stop conditions>

结束时提交 Research Handoff，列出精确文件、命令、结果、限制和下一个工作包。
```

## 13. Definition of Ready

Work Package 可开始的条件：

- 目标、范围、非范围明确；
- 上游接口稳定；
- 必要 RCP 已批准；
- 文件 owner 唯一；
- baseline clean；
- acceptance test 可描述；
- 真实人审责任人明确；
- migration/rollback 要求明确；
- 没有隐藏的许可或 secret 问题。

## 14. Definition of Done

- 功能按批准语义完成；
- 没有扩大范围；
- 自动和真实 Gate 按阶段要求完成；
- 文档、内部 adapter help、Schema、UI 一致；
- validate/index/test/lint/type 通过；
- worktree 变更可解释；
- 没有 secret/受限资产；
- 交接完整；
- 需人工决定的内容未被 Agent 擅自关闭。
