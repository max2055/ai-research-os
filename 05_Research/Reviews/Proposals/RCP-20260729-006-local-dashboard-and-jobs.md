# Rule Change Proposal

Proposal ID：RCP-20260729-006

状态：approved

创建日期：2026-07-29

提议人：Codex

## Target

- local read-only FastAPI/HTMX Dashboard
- Obsidian Home Dashboard derived index
- Job Run operational object and scheduler entrypoints
- UI/test dependencies and packaged CSS

## Observed problem

核心工作流已可通过 CLI 运行，但研究者仍需记住命令、跨目录查看对象，无法在一个
入口检查 review queue、Thesis health、Source provenance、metrics change、逾期
Action 和任务失败。

## Evidence

- Roadmap：`00_System/Productization_Roadmap_v1.md` M5-01～M5-10。
- M2 已提供 project/review/action query。
- M3 已提供 Source asset integrity。
- M4 已提供 citation、incremental metrics state 和 Report lifecycle。

## Proposed change

1. 增加只绑定 loopback 的 FastAPI Dashboard；所有产品页只有 GET。
2. 页面每次从 Markdown 重建，不把 Dashboard cache 作为事实源。
3. HTMX 只用于只读 fragment enhancement；无 JavaScript 时普通链接和表单仍可用。
4. 增加 `Home_Dashboard.md` 全局和 Project 级派生 index，可由 `index --apply`
   完整重建。
5. 增加 Job Run：

```yaml
id: JOB-YYYYMMDDhhmmss-NNN
type: job
status: success|failed
job_name: validate|indexes|metrics|source-process|refresh
started_at:
finished_at:
target:
message:
```

6. 每次 scheduler job 追加 Job Run；失败不会伪装成功，Dashboard/Obsidian health
   可见。业务动作保持幂等，audit record 保持追加。

## Security and scope

- Dashboard 默认且强制绑定 `127.0.0.1`、`localhost` 或 `::1`。
- v1 无账户、无公网部署、无写入 endpoint、无正文编辑。
- Source asset 只能按 Source-owned path 的数字 index 读取，不能传任意 path。
- UI 对所有仓库文本做 HTML escape。
- Dashboard 不触发 Review Decision，不改变 Thesis confidence。

## Alternatives considered

- 单页静态 HTML：拒绝；无法持续反映 Markdown 和 project filter。
- 带编辑表单的 Web app：延后；扩大授权与数据损坏风险。
- 把 UI cache 当数据库：拒绝；违反 Markdown source of truth。
- 不记录 scheduler failure：拒绝；会形成静默 stale 状态。

## Migration

无权威研究对象迁移。新增一个可重建 Home index；Job Run 只在显式运行 job 后追加。

## Acceptance tests

- Homepage、Review filters、Source、Thesis、Metrics、Operations、Health 与 API
  都能从隔离 Markdown fixture 返回。
- App 不注册 POST/PUT/DELETE。
- Source asset path 无法越权访问。
- Home index 删除后可重建。
- success/failed Job Run 均可验证并在 health 显示。
- metrics job 同日重跑不覆盖不同内容；相同内容为 no-op。
- refresh job 后 global/project index drift 为 0。
- 非 loopback host 拒绝启动。

## Human decision

- Decision: approve
- Reviewer: max
- Date: 2026-07-29
- Reason: 用户已批准完整产品化路线；Dashboard 保持 local-only/read-only。

## Implementation record

- Changed files: local Dashboard app/CSS、Job Schema/service、CLI、Home index、
  metadata/design/runbook、dependencies 与 tests。
- Migration: none；新增 global/PRJ-001 Home derived index；真实仓库未创建 Job Run。
- Test result: 86/86；83% coverage；Ruff 与 mypy strict 通过。
- Runtime smoke: loopback Overview、Review filter、API 200；clean shutdown。
- Validation result: 56/56 formal Schema；0 error；18 个既有 REV003 warning；
  global/PRJ-001 8/8 index drift 0。
- Effective date: 2026-07-29
