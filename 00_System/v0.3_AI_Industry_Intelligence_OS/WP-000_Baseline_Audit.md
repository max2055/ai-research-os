# WP-000 Baseline Audit — v0.2 Evidence Kernel

状态：`pending`（Agent 生成的只读快照，非正式发布结论）
日期：2026-08-05
Baseline commit：`ff5c82b`
环境：`/Users/max/.venvs/ai-research-os`（Python 3.13.9），`pip install -e ".[dev,ui]"`

## 1. 基线数字

| 检查 | 结果 | Gate |
|---|---|---|
| `research-os doctor` | PASS（所有项） | — |
| `research-os validate` | 0 errors / 0 warnings | 0 error |
| Index global | 0 drift | 0 drift |
| Index PRJ-001 | 0 drift | 0 drift |
| Index PRJ-002 | **1 drift**（`08_Indexes/Projects/PRJ-002/Company_Index.md`） | 0 drift |
| pytest | 98 passed | — |
| Coverage | 84.28% | ≥80% |
| ruff | pass | pass |
| mypy strict | pass（51 source files） | pass |
| Release check | 13/18 PASS | ready=no |

正式对象：166（source=39, event=31, thesis=8, company=8, report=2, project=2, review=64, action=12）。

## 2. v0.2 发布闸门

`research-os release check` 结果为 13/18 PASS，5 个 BLOCKED：

| 闸门 | 原因 | 性质 |
|---|---|---|
| `indexes.pilot` | PRJ-002 索引漂移 1 文件 | 可修复 |
| `pilot.cadence.weekly` | 0/2 已完成真实 Weekly review | 时间闸门 |
| `pilot.cadence.monthly` | 0/1 已完成真实 Monthly review | 时间闸门 |
| `pilot.actions` | ACT-20260729-009 未解决 | cadence Action |
| `release.human_decision` | 最终人工 v0.2 发布决定 pending | 人工决定 |

其余闸门全部 PASS：repository.validation、indexes.global、pilot.project、pilot.sources（12/12）、pilot.events（9/9）、pilot.report（1/1）、m4.field_gate（10/10）、research_quality.actions（RQ-01~08）、engineering.performance、engineering.recovery、release.documents。

## 3. 已确认漂移

- `08_Indexes/Projects/PRJ-002/Company_Index.md` 与 canonical 输出不一致（PRJ-002 项目级索引漂移）。全局与 PRJ-001 均无漂移。
- 按交接文档要求作为独立小任务处理，不混入其他工作包。

## 4. 结论

- 基线健康：对象完整、validate/index/test/lint/type 全部通过，足以作为 v0.3 建设基础。
- v0.2 正式发布仍被 5 个闸门阻塞：1 个可修复（PRJ-002 漂移）、1 个 cadence Action、2 个时间闸门（Weekly/Monthly）、1 个最终人工决定。这些与 WP-001（日期阻塞）一致。
- 建议下一步：WP-010（RCP-v03-001 草稿）；PRJ-002 漂移作独立小任务。

## 5. 限制

- 无远程 git remote；Source assets 按 Source_Policy 排除在 Git 外（单独加密备份）。
- 本快照为 Agent 产物，尚未人工批准。
