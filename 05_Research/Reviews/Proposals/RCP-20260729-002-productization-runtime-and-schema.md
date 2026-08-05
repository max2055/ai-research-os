# Rule Change Proposal

Proposal ID：RCP-20260729-002

状态：approved

创建日期：2026-07-29

提议人：Codex

## Target

- Python package 与 CLI 运行方式
- 正式对象 Schema
- Markdown front matter round-trip
- 开发、测试、lint、type check 与本地 Dashboard 依赖

## Observed problem

当前自动化由 `09_Automation/research_os.py` 与 2,000 行以上的单体 core 文件组成，没有可安装 package、正式类型 Schema、注释保留型 YAML writer、统一开发依赖或 CI。

## Evidence

- Metrics snapshot: `05_Research/Reviews/Snapshots/METRICS-20260729.json`
- Review: `00_System/Productization_Roadmap_v1.md`
- Affected object IDs: 当前 49 个核心研究对象
- Test or validation output: M0 为 33 tests、0 error、0 index drift

## Proposed change

采用以下产品化运行时：

- Python `>=3.12`
- setuptools + `pyproject.toml`
- Pydantic v2：正式 Schema 与可解释错误
- ruamel.yaml：保留 front matter 顺序、注释和人工格式
- Typer：产品化 CLI
- FastAPI + Uvicorn：后续本地只读 Dashboard
- pytest + coverage：测试与覆盖率
- Ruff：lint 与 format
- mypy：核心类型检查

约束：

- Markdown 继续是唯一研究事实源。
- Pydantic 负责验证，不接管人工正文。
- round-trip 写入必须保留正文、未知字段、键顺序和注释。
- 迁移默认 dry-run，apply 前生成备份和变更清单。
- 现有 `09_Automation/research_os.py` 命令至少兼容一个版本周期。

## Alternatives considered

- 继续只使用标准库：依赖少，但 Schema、CLI、YAML round-trip 和 Web 产品层返工更大。
- 直接迁移数据库：拒绝；当前规模未触发，且会引入第二事实源风险。
- 使用 PyYAML：拒绝；无法满足注释和人工格式保留要求。

## Risks

- 依赖升级造成行为变化。
- Pydantic coercion 静默改变数据类型。
- YAML writer 造成大面积无意义 diff。
- Python 3.14 本地环境可能暴露依赖兼容问题。

控制：

- 使用兼容版本范围和 lock/CI 记录。
- Schema 默认严格验证关键字段。
- 先做 read/round-trip dry-run 和 hash 清单，不直接迁移 49 个对象。
- 保留 legacy CLI golden tests。

## Migration

1. 建立 `pyproject.toml` 与 `src/research_os`。
2. 先移动兼容内核，不改变研究对象。
3. 分类型引入 Schema 并对全部对象执行只读验证。
4. round-trip 先写临时目录并比较 front matter 语义与正文 hash。
5. 只有 dry-run 全绿后才执行 metadata migration。

## Acceptance tests

- editable install 后 `research-os doctor` 通过。
- 旧 CLI 命令继续通过 subprocess tests。
- 49 个对象通过新旧 validator。
- round-trip 保留正文、未知字段和注释。
- lint、type check、test、validate、index 全绿。

## Human decision

- Decision: approve
- Reviewer: max
- Date: 2026-07-29
- Reason: 用户已批准完整产品化计划及依赖引入；方案保持 Markdown 事实源和人工审核边界。

## Implementation record

- Changed files: `pyproject.toml`、`.github/workflows/ci.yml`、`src/research_os`、兼容入口、tests、运行文档
- Test result: 44 tests passed；product core coverage 89.88%；Ruff 和 mypy 通过
- Validation result: legacy validator 0 error；formal Schema 49/49；0 index drift
- Effective date: 2026-07-29
